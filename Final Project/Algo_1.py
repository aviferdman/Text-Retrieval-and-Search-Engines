from pyserini.analysis import Analyzer, get_lucene_analyzer
from pyserini.search.lucene import LuceneSearcher, LuceneFusionSearcher
from Reranker import load_model_and_predict, read_scores_from_files,train_reranker

def algo1(queries, index_path, output_file='run_1.res', k1=0.9, b=0.4,
          fb_terms=10, fb_docs=10, original_query_weight=0.5):
    """
    BM25 with RM3 query expansion and LambdaMART reranking.

    Parameters:
        queries (list): List of tuples (query_id, query_text).
        index_path (str): Path to the Lucene index.
        output_file (str): File to save reranked results for test queries.
        k1 (float): BM25 k1 parameter.
        b (float): BM25 b parameter.
        fb_terms (int): Number of feedback terms for RM3.
        fb_docs (int): Number of feedback documents for RM3.
        original_query_weight (float): Weight of the original query in RM3 expansion.

    Returns:
        None
    """
    # Initialize searcher with BM25 and RM3 settings
    searcher = LuceneSearcher(index_path)
    analyzer = get_lucene_analyzer(stemmer='krovetz', stopwords=False)
    searcher.set_analyzer(analyzer)
    searcher.set_bm25(k1=k1, b=b)
    searcher.set_rm3(fb_terms=fb_terms, fb_docs=fb_docs, original_query_weight=original_query_weight)

    # Save BM25+RM3 results for training on the first 50 queries
    train_file = 'train_res.res'
    with open(train_file, 'w') as f_train:
        for query_id, query_text in queries[:50]:  # First 50 queries for training
            hits = searcher.search(query_text, k=1000)
            for i, hit in enumerate(hits):
                f_train.write(f"{query_id} Q0 {hit.docid:<17} {i + 1:<4} {hit.score:<20.6f} run_1_train\n")

    # Train LambdaMART reranker using the first 50 queries
    model = train_reranker([('train_res.res', 'run_1_train')])

    # Perform BM25+RM3 for testing on the remaining queries and rerank
    test_file = 'test_res.res'
    with open(test_file, 'w') as f_test:
        for query_id, query_text in queries[50:]:  # Remaining queries for testing
            hits = searcher.search(query_text, k=1000)
            for i, hit in enumerate(hits):
                f_test.write(f"{query_id} Q0 {hit.docid:<17} {i + 1:<4} {hit.score:<20.6f} run_1_test\n")

    # Read testing results and prepare for reranking
    test_df = read_scores_from_files([('test_res.res', 'run_1_test')])

    # Rerank and save results for test queries
    load_model_and_predict(model, test_df, output_file)

    print(f"Reranked results for test queries saved to {output_file}")

