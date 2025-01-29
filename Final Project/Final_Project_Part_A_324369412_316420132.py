from Algo_1 import algo1
from Algo_2 import algo2
from Algo_3 import algo3
from helpers import *

QUERIES_PATH =  r'files/queriesROBUST.txt'
INDEX_PATH = r'RobustPyserini'
QRELS_PATH = r'files/qrels_50_Queries'

def main():
    queries = get_queries_list(QUERIES_PATH)
    algo1(queries, index_path=INDEX_PATH, k1=0.9, b=0.4, fb_terms=26, fb_docs=30, original_query_weight=0.7)
    algo2(queries, index_path=INDEX_PATH, output_file='run_2.res', mu=800, fb_terms=50, fb_docs=20,
          original_query_weight=0.7, hybrid_weight=0.5)
    algo3(queries, index_path=INDEX_PATH, fusion_method='rrf', runs=['run_1.res', 'run_2.res'],
          output_file='run_3.res', fusion_k=90, k1=0.9, b=0.2)
if __name__ == '__main__':
    main()