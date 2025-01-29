from pyserini.analysis import Analyzer, get_lucene_analyzer
from pyserini.search.lucene import LuceneSearcher, LuceneFusionSearcher

def normalize_scores(hits):
    if not hits:  # Handle empty results
        return hits
    scores = [hit.score for hit in hits]
    min_score = min(scores)
    max_score = max(scores)
    if max_score > min_score:
        normalized_scores = [(score - min_score) / (max_score - min_score) for score in scores]
    else:
        normalized_scores = [0.0 for _ in scores]
    for hit, norm_score in zip(hits, normalized_scores):
        hit.score = norm_score
    return hits

def get_queries_list(queries_path):
    queries = []
    with open(queries_path, 'r', encoding='utf-8') as q_file:
        for line in q_file:
            line = line.strip()
            if line:  # Skip empty lines
                parts = line.split('\t')  # Split line by tab character
                if len(parts) == 2:  # Ensure it has both id and query
                    query_id, query_text = parts
                    queries.append((query_id, query_text))
        return queries

def plain_bm25(queries, index_path, output_file='bm25.res', k1=0.9, b=0.4):
    """
    Plain BM25 without RM3 - for algo3
    """
    searcher = LuceneSearcher(index_path)
    analyzer = get_lucene_analyzer(stemmer='krovetz', stopwords=False)
    searcher.set_analyzer(analyzer)
    searcher.set_bm25(k1=k1, b=b)
    with open(output_file, 'w') as f:
        for query in queries:
            hits = searcher.search(query[1], k=1000)
            # hits = normalize_scores(hits)
            for i, hit in enumerate(hits):
                f.write(f"{query[0]} Q0 {hit.docid:<17} {i+1:<4} {hit.score:<20.6f} run_bm25\n")