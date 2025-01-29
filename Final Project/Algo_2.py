from pyserini.search.lucene import LuceneSearcher
from pyserini.analysis import Analyzer, get_lucene_analyzer
from collections import defaultdict
from Reranker import load_model_and_predict, read_scores_from_files,train_reranker

def normalize_scores(hits):
    """
    Normalize scores using Min-Max normalization.
    """
    if not hits:
        return hits
    scores = [hit.score for hit in hits]
    min_score = min(scores)
    max_score = max(scores)
    if max_score > min_score:
        for hit in hits:
            hit.score = (hit.score - min_score) / (max_score - min_score)
    else:
        for hit in hits:
            hit.score = 0.0
    return hits


def combine_scores(hits_qld, hits_bm25, weight_qld=0.7):
    """
    Combine scores from QLD and BM25.
    """
    combined_scores = defaultdict(float)
    for hit_qld, hit_bm25 in zip(hits_qld, hits_bm25):
        combined_scores[hit_qld.docid] += weight_qld * hit_qld.score
        combined_scores[hit_bm25.docid] += (1 - weight_qld) * hit_bm25.score

    # Sort combined scores
    combined_hits = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return combined_hits

def algo2(queries, index_path, output_file='run_2.res', mu=1000, fb_terms=10, fb_docs=10, original_query_weight=0.5, hybrid_weight=0.5):
    """
    Query Likelihood with Dirichlet priors smoothing, RM3-based query expansion, and hybrid scoring.

    Parameters:
        queries (list): List of tuples (query_id, query_text).
        index_path (str): Path to the Lucene index.
        output_file (str): File to save reranked results for test queries.
        mu (float): Dirichlet prior smoothing parameter.
        fb_terms (int): Number of feedback terms for RM3.
        fb_docs (int): Number of feedback documents for RM3.
        original_query_weight (float): Weight of the original query in RM3 expansion.
        hybrid_weight (float): Weight for combining QLD and BM25 scores.

    Returns:
        None
    """
    # Initialize QLD searcher
    searcher_qld = LuceneSearcher(index_path)
    analyzer = get_lucene_analyzer(stemmer='krovetz', stopwords=False)
    searcher_qld.set_analyzer(analyzer)
    searcher_qld.set_qld(mu=mu)

    # Initialize BM25+RM3 searcher
    searcher_bm25 = LuceneSearcher(index_path)
    searcher_bm25.set_analyzer(analyzer)
    searcher_bm25.set_bm25(k1=0.9, b=0.4)
    searcher_bm25.set_rm3(fb_terms=fb_terms, fb_docs=fb_docs, original_query_weight=original_query_weight)

    # Save combined scores for training on the first 50 queries
    train_file = 'train_res.res'
    with open(train_file, 'w') as f_train:
        for query_id, query_text in queries[:50]:  # First 50 queries for training
            hits_qld = searcher_qld.search(query_text, k=1000)
            hits_bm25 = searcher_bm25.search(query_text, k=1000)
            combined_hits = combine_scores(hits_qld, hits_bm25, weight_qld=hybrid_weight)
            normalized_hits = sorted(combined_hits, key=lambda x: x[1], reverse=True)
            for rank, (doc_id, score) in enumerate(normalized_hits, start=1):  # Write up to 1000 results
                f_train.write(f"{query_id} Q0 {doc_id:<17} {rank:<4} {score:<20.6f} run_2_train\n")

    # Train LambdaMART reranker using the first 50 queries
    model = train_reranker([('train_res.res', 'run_2_train')])

    # Perform scoring for testing on the remaining queries and rerank
    test_file = 'test_res.res'
    with open(test_file, 'w') as f_test:
        for query_id, query_text in queries[50:]:  # Remaining queries for testing
            hits_qld = searcher_qld.search(query_text, k=1000)
            hits_bm25 = searcher_bm25.search(query_text, k=1000)
            combined_hits = combine_scores(hits_qld, hits_bm25, weight_qld=hybrid_weight)
            normalized_hits = sorted(combined_hits, key=lambda x: x[1], reverse=True)
            for rank, (doc_id, score) in enumerate(normalized_hits[:1000], start=1):  # Write available results
                f_test.write(f"{query_id} Q0 {doc_id:<17} {rank:<4} {score:<20.6f} run_2_test\n")

    # Read testing results and prepare for reranking
    test_df = read_scores_from_files([('test_res.res', 'run_2_test')])

    # Rerank and save results for test queries
    load_model_and_predict(model, test_df, output_file)

    print(f"Reranked results for test queries saved to {output_file}")

