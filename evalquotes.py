"""Quote attribution evaluation.

Usage: evalquotes.py <gold.xml> <outputprefix> <goldfilesprefix>

where `gold.xml` is a file produced by https://github.com/muzny/quoteannotator/
and `outputprefix` is a prefix as used by dutchcoref;
and 'goldfilesprefix' is a prefix to get the goldfiles produced by dutchcoref

Usage example:
$ python3 evalquotes.py quotes/Voskuil_Buurman.xml /tmp/Voskuil_Buurman /goldfiles/Voskuil_Buurman/Voskuil_Buurman

"""
import sys
from lxml import etree
import pandas

VERBOSE = False

class Goldquote:
	def __init__(self, text, connection, glob_begin, begin, end, mention):
		"""
		:param text: text of quote as string
		:param speaker: speaker of quote as string
		:param connection: id of mention that quote is connected to as string
		:param id: id of quote as string
		:param parno: paragraph number
		:param sentno: sentence number within paragraph
		:param begin: begin token number within sentence
		:param end: end token number within sentence
		:param glob_begin: global begin token number
		:param mention: Mention xml element of this quote's speaker.
		"""
		self.text = text
		self.connection = connection
		self.glob_begin = glob_begin
		self.begin, self.end = begin, end
		self.mention = mention


def print_report(correct, nospeaker, n):
	"""Prints precision, recall and F1-score"""
	print(f"Precision: {correct} / {n - nospeaker} = {correct / (n - nospeaker):.3f}")
	print(f"Recall: {correct} / {n} = {correct / n:.3f}")
	print(f"F score: {2 * (correct / (n - nospeaker) * (correct / n)) / (correct / (n - nospeaker) + (correct / n)):.3f}")
	print(f"No speaker:", nospeaker)


def main():
	try:
		goldfile, outputprefix, goldprefix = sys.argv[1:]
	except Exception:
		print(__doc__)
		return

	# Get candidate- and gold quotes and mentions from xml and tsv files
	cand_quotes = pandas.read_csv(
		outputprefix + '.quotes.tsv', sep='\t', quoting=3)
	cand_mentions = pandas.read_csv(
		outputprefix + '.mentions.tsv', sep='\t', quoting=3)
	gold = etree.parse(goldfile)
	gold_mentions = pandas.read_csv(
		goldprefix + '.mentions.tsv', sep='\t', quoting=3)
	gold_clusters = pandas.read_csv(
		goldprefix + '.clusters.tsv', sep='\t', quoting=3)

	# Make dict of gold quote objects with start token as key
	goldquotes = dict()
	for qe in gold.findall('.//quote'):
		text = " ".join(qe.itertext()).strip()
		text = ' '.join(text.split())
		connection = qe.get("connection")
		mention = gold.find(f".//mention[@id='{connection}']")
		quote_obj = Goldquote(text, connection, int(qe.get("ttokenno")),
							  int(qe.get("begin")), int(qe.get("end")), mention)
		goldquotes[quote_obj.glob_begin] = quote_obj

	# Collect predictions
	correct = 0
	nospeaker = 0
	n = 0
	cluster_correct = 0

	for (_, row) in cand_quotes.iterrows():
		# Take quotes that are correctly extracted and have a gold speaker
		if row.start in goldquotes and goldquotes[row.start].mention is not None:
			# Compare speaker and mention if quote text is the same
			goldquote = goldquotes[row.start]
			if goldquote.text != row.text and VERBOSE:
				print(f"Warning! detected text differs:\nGOLD: {goldquote.text}\nDETECTED: {row.text}\n")

			if row.speakermention == "-":  # No speaker assigned by system
				nospeaker += 1

			else:  # Speaker assigned by system
				# EVALUATE MENTION:
				# Get start and end tokenno of gold mention
				me = goldquote.mention
				start = int(me.get("ttokenno"))
				end = start + (int(me.get("end")) - int(me.get("begin")))
				# Get start and end tokenno of system mention
				r = cand_mentions[cand_mentions["id"] == int(row.speakermention)]
				start2, end2 = r["start"].values[0], r["end"].values[0]
				correct += (start == start2 and end == end2)

				# EVALUATE CLUSTER:
				# Find cluster id to which the gold mention belongs
				try:
					clusterid = gold_mentions[(gold_mentions['start'] == start) & (gold_mentions['end'] == end)]["cluster"].values[0]
				except IndexError:
					if VERBOSE:
						print(f"Mention not in goldmention tsv: {me.text}\t {start}\t {end}")
					n += 1
					cluster_correct += (start == start2 and end == end2)
					continue
				# Get all ids of all mentions in gold cluster
				mention_ids = gold_clusters[gold_clusters['id'] == clusterid]['mentions'].values[0].split(",")
				index_tuplist = []
				for id in mention_ids:
					startno = gold_mentions[gold_mentions['id'] == int(id)]['start'].values[0]
					endno = gold_mentions[gold_mentions['id'] == int(id)]['end'].values[0]
					index_tuplist.append((startno, endno))
				# See whether system mention's start and end token are in the gold cluster
				cluster_correct += (start2, end2) in index_tuplist
			n += 1

	print("## Mention scores ##")
	print_report(correct, nospeaker, n)
	print("\n## Cluster scores ##")
	print_report(cluster_correct, nospeaker, n)


if __name__ == '__main__':
	main()
