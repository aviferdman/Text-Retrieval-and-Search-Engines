from collections import defaultdict

def reciprocal_rank_fusion(run_files, k=100):
    """
    Perform Reciprocal Rank Fusion (RRF) on multiple TREC run files.
    """
    fused_results = defaultdict(lambda: defaultdict(float))

    # Read each run file and calculate RRF scores
    for run_file in run_files:
        with open(run_file, 'r') as f:
            for line in f:
                query_id, _, doc_id, rank, _, _ = line.strip().split()
                rank = int(rank)
                fused_results[query_id][doc_id] += 1 / (k + rank)

    # Sort results for each query by descending RRF score
    for query_id in fused_results:
        fused_results[query_id] = sorted(
            fused_results[query_id].items(), key=lambda x: x[1], reverse=True)

    return fused_results

def algo3(queries, fusion_method, index_path, fusion_k=100,
          runs=['run_1.res', 'run_2.res'], k=1000,
          output_file='run_3.res', k1=0.9, b=0.4):
    """
    Fuse results from multiple runs using the specified fusion method.
    """

    fused_results = reciprocal_rank_fusion(runs, k=fusion_k)
    with open(output_file, 'w') as f:
        for query_id, doc_scores in fused_results.items():
            # Keep only the top k documents for each query
            top_k_docs = doc_scores[:k]
            for rank, (doc_id, score) in enumerate(top_k_docs, start=1):
                f.write(f"{query_id} Q0 {doc_id} {rank} {float(score):.6f} run_3\n")