import lightgbm as lgb
import numpy as np
import pandas as pd
from evaluate_project import print_eval

# Constants
QUERIES_PATH = r'files/queriesROBUST.txt'
INDEX_PATH = r'RobustPyserini'
QRELS_PATH = r'files/qrels_50_Queries'
MODEL_PATH = 'lambdamart_model.pkl'
PREDICTION_OUTPUT = 'lambdamart_predictions.res'


def load_qrels(qrels_path):
    """
    Load qrels into a dictionary.
    """
    qrels = {}
    with open(qrels_path, 'r') as f:
        for line in f:
            query_id, _, doc_id, relevance = line.strip().split()
            if query_id not in qrels:
                qrels[query_id] = {}
            qrels[query_id][doc_id] = int(relevance)
    return qrels


def get_queries_list(queries_path):
    """
    Load queries from a file.
    """
    queries = []
    with open(queries_path, 'r', encoding='utf-8') as f:
        for line in f:
            query_id, query_text = line.strip().split('\t')
            queries.append((query_id, query_text))
    return queries

def read_scores_from_files(run_files, qrels_path=QRELS_PATH):
    """
    Read scores and relevance data from multiple run files into a single DataFrame.
    Each run file contributes its score and rank as separate columns.

    Parameters:
        run_files (list): List of tuples where each tuple contains (run_file_path, run_name).
                          The run_name is used for column naming.
        qrels_path (str): Path to the qrels file.

    Returns:
        pd.DataFrame: A combined DataFrame with scores, ranks, and relevance for each document.
    """
    qrels = load_qrels(qrels_path)

    # Parse all run files into a dictionary for quick lookups
    run_data = {}
    for run_file, run_name in run_files:
        with open(run_file, 'r') as f:
            for line in f:
                query_id, _, doc_id, rank, score, _ = line.strip().split()
                if query_id not in run_data:
                    run_data[query_id] = {}
                if doc_id not in run_data[query_id]:
                    run_data[query_id][doc_id] = {}
                run_data[query_id][doc_id][f'{run_name}_score'] = float(score)
                run_data[query_id][doc_id][f'{run_name}_rank'] = int(rank)

    data = []  # Use a list to collect rows

    # Iterate over all entries in the first run file to form the base DataFrame
    primary_run = run_files[0][1]
    for query_id, docs in run_data.items():
        for doc_id, doc_scores in docs.items():
            # Combine scores and ranks from all runs
            row = {
                'query_id': query_id,
                'doc_id': doc_id,
                'relevance': qrels.get(query_id, {}).get(doc_id, 0)
            }
            row.update(doc_scores)
            data.append(row)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(data)

    return df


def split_train_val_by_query(df, train_size=800, val_size=200, random_state=None):
    """
    Split the DataFrame into train and validation sets for each query ID.
    The data is shuffled for each query before splitting.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing query and document data.
        train_size (int): Number of rows per query for the training set.
        val_size (int): Number of rows per query for the validation set.
        random_state (int, optional): Random seed for reproducibility.

    Returns:
        pd.DataFrame, pd.DataFrame: Training and validation DataFrames.
    """
    train_data = []
    val_data = []

    for query_id, group in df.groupby('query_id'):
        # Shuffle the group before splitting
        group = group.sample(frac=1, random_state=random_state).reset_index(drop=True)
        # Split into train and validation
        train_data.append(group.iloc[:train_size])
        val_data.append(group.iloc[train_size:train_size + val_size])

    # Concatenate all groups into train and validation DataFrames
    train_df = pd.concat(train_data).reset_index(drop=True)
    val_df = pd.concat(val_data).reset_index(drop=True)

    return train_df, val_df

def predict_and_rerank(test_df, model, output_file):
    """
    Predict scores for test data and rerank documents for each query.
    """
    # Prepare test data
    X_test = test_df.drop(["query_id", "doc_id", "relevance"], axis=1)

    # Generate predictions
    test_df["predicted_score"] = model.predict(X_test)

    # Group by query_id and rerank based on predicted scores
    reranked_results = []
    for query_id, group in test_df.groupby("query_id"):
        group = group.sort_values(by="predicted_score", ascending=False)
        for rank, (_, row) in enumerate(group.iterrows(), start=1):
            reranked_results.append(
                f"{query_id} Q0 {row['doc_id']} {rank} {row['predicted_score']:.6f} {output_file[:-4]}"
            )

    # Save reranked results in TREC format
    with open(output_file, "w") as f:
        f.write("\n".join(reranked_results) + "\n")

    print(f"Predictions saved to {output_file}")
    print_eval(
        run_files={'reranked': output_file},
        qrels_path=QRELS_PATH
    )

def train_reranker(run_files=[('run_1.res','bm25')]):
    bm_df = read_scores_from_files(run_files)
    train_df, validation_df = split_train_val_by_query(bm_df, random_state=42)

    qids_train = train_df.groupby("query_id")["query_id"].count().to_numpy()
    X_train = train_df.drop(["query_id", "doc_id", "relevance"], axis=1)
    y_train = train_df["relevance"]


    qids_validation = validation_df.groupby("query_id")["query_id"].count().to_numpy()
    X_validation = validation_df.drop(["query_id", "doc_id", "relevance"], axis=1)
    y_validation = validation_df["relevance"]

    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
    )

    model.fit(
        X=X_train,
        y=y_train,
        group=qids_train,
        eval_set=[(X_validation, y_validation)],
        eval_group=[qids_validation]
    )

    return model

def load_model_and_predict(model, test_df, output_file):
    """
    Load a saved LightGBM model, predict scores for test data, and save reranked results in TREC format.

    Parameters:
        test_df (pd.DataFrame): The test DataFrame containing features and query/document identifiers.
        model_path (str): Path to the saved LightGBM model file.
        output_file (str): Path to save the TREC-formatted reranked results.

    Returns:
        None
    """

    # Prepare test data
    X_test = test_df.drop(["query_id", "doc_id", "relevance"], axis=1)

    # Generate predictions
    test_df["predicted_score"] = model.predict(X_test)

    # Group by query_id and rerank based on predicted scores
    reranked_results = []
    for query_id, group in test_df.groupby("query_id"):
        group = group.sort_values(by="predicted_score", ascending=False)
        for rank, (_, row) in enumerate(group.iterrows(), start=1):
            reranked_results.append(
                f"{query_id} Q0 {row['doc_id']} {rank} {row['predicted_score']:.6f} {output_file[:-4]}"
            )

    # Save reranked results in TREC format
    with open(output_file, "w") as f:
        f.write("\n".join(reranked_results) + "\n")

    print(f"Predictions saved to {output_file}")
