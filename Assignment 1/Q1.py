from collections import defaultdict
import re
import os
import zipfile
from tempfile import TemporaryDirectory

class InvertedIndex:
	def __init__(self):
		"""
		Initialize the data structure of the inverted index,
		implemented as learned at class and described at HW.
		"""
		self.index = defaultdict(list) # InvertedIndex data sreucture
		self.doc_ids = {} # Doc Id (key) to Doc name (value) dictionary

	def add_document(self, doc_path):
		"""
		Add a new document to the InvertedIndex structure.
		@doc_path - relative path to document
		"""
		# add mapping of Document name to Document ID
		doc_id = len(self.doc_ids)
		self.doc_ids[doc_id] = doc_path.split('/')[-1]

		# open and parse document, create set of words and add it to data sreucture.
		with open(doc_path, 'r') as file:
			document = file.read()
			text = re.search(r"<TEXT>(.*?)</TEXT>", document, re.DOTALL)
			words = text.group(1).strip()
			sob = set(words.split())
			for word in sob:
				self.index[word].append(doc_id)

	def print(self):
		"""
		print inverted index
		"""
		for word, docs in sorted(self.index.items()):
			postings = "-> ".join(f'{idx + 1} ({self.doc_ids[idx]})' for idx in docs)
			print(f'{word} -> {postings}')

def main():
	count = 0
	index = InvertedIndex()

	curr_dir = os.path.dirname(os.path.abspath(__file__))
	data_dir = os.path.join(curr_dir, "data")

	if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
		print("No 'data' folder found")
		return

	for zip_name in os.listdir(data_dir):
		zip_path = os.path.join(data_dir, zip_name)

		with TemporaryDirectory() as temp_dir:
			with zipfile.ZipFile(zip_path, 'r') as zip_ref:
				zip_ref.extractall(temp_dir)

			for root, _, files in os.walk(temp_dir):
				for file in files:
					file_path = os.path.join(root, file)
					index.add_document(file_path)

	index.print()

if __name__ == "__main__":
	main()