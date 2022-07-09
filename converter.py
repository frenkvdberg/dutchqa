#!/usr/bin/env python

"""
Filename:   converter.py
Author:    Frank van den Berg
Description:
    With -a create: Converts dutchcoref booknlp format to xml format, adding
    characters, quotes and mentions.
    example usage:
    $ python3 converter.py -a create -b goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.conll
    -m goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.mentions.tsv
    -q goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.quotes.tsv
    -c goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.clusters.tsv

    With -a update: Updates characterlist as well as mention- and quote tag
    attributes AFTER annotating with the Muzny quoteannotator tool.
    example usage:
    $ python3 converter.py -a update -x Abdolah_Koning_annotated.xml -b goldfiles/Abdolah_Koning/Abdolah_Koning.conll
"""

import argparse
import pandas as pd
import re
import xml.etree.ElementTree as ET
import os
import sys


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", default='create', type=str,
                        help="Action to perform: 'create' to create xml file or 'update' to update the"
                             " tags of an xml file with sentno, start, end- information.",
                        choices=["create", "update"])
    parser.add_argument("-b", "--booknlp", type=str,
                        help="booknlp conll file, being dutchcoref output in booknlp format")
    parser.add_argument("-m", "--mentions", type=str,
                        help="mentions tsv file, being dutchcoref output containing mentions")
    parser.add_argument("-q", "--quotes", type=str,
                        help="quotes tsv file, being dutchcoref output containing quotes")
    parser.add_argument("-c", "--clusters", type=str,
                        help="clusters tsv file, being dutchcoref output containing clusters")
    parser.add_argument("-x", "--xml", type=str,
                        help="xml file of which the tags need to be updated")
    args = parser.parse_args()
    return args


def create_characters_dict(quotes_df, clusters_df):
    """Returns a dictionary containing speakercluster ids and their labels"""
    characters = dict()

    # Get unique speakerclusters and store their labels in a dictionary
    speakerclusters = quotes_df['speakercluster'].unique()
    for sc in speakerclusters:
        if sc != '-':
            cluster_info = clusters_df.loc[clusters_df['id'].astype(str) == sc]
            characters[sc] = cluster_info['label'].item()

    return characters


def create_mentions_dict(quotes_df, mentions_df):
    """Returns a nested dict containing {'start': {'id': x, 'end': y, 'cluster': z}} for each mention"""
    mentions = dict()

    # Get unique speakermentions and create dictionary
    speakermentions = quotes_df['speakermention'].unique()
    for sm in speakermentions:
        if sm != "-":
            mention_info = mentions_df.loc[mentions_df['id'].astype(str) == sm]
            start, end = mention_info['start'].item(), mention_info['end'].item()
            cluster = mention_info['cluster'].item()
            mentions[start] = {'id': sm, 'end': end, 'cluster': cluster}

    return mentions


def update_qm_lists(quotelist, mentionlist, line, parno, sentno, total_tokens):
    """Creates lists with (parno, sentno, tokenno, total_tokenno, typestring) tuples for
    the mentions and quotes"""
    # Replace <quote>, </quote>, <mention> and </mention> tags:
    line = re.sub('<quote .*?>', 'BQUOTE ', line)
    line = re.sub('</quote>', ' EQUOTE', line)
    line = re.sub('<mention .*?>', 'BMENTION ', line)
    line = re.sub('</mention>', ' EMENTION', line)
    # Remove all other tags:
    line = re.sub('<.*?>', "", line.strip())
    # Update quote and mention lists with (parno, sentno, tokenno, total_tokenno, typestring) tuples.
    tokenno = 0
    for token in line.split():
        if token == 'BQUOTE':
            quotelist.append((parno, sentno, tokenno, total_tokens, 'BQUOTE'))
        elif token == 'EQUOTE':
            if tokenno == 0:
                quotelist.append((parno, sentno-1, tokenno, total_tokens, 'EQUOTE'))
            else:
                quotelist.append((parno, sentno, tokenno, total_tokens, 'EQUOTE'))
        elif token == 'BMENTION':
            mentionlist.append((parno, sentno, tokenno, total_tokens, 'BMENTION'))
        elif token == 'EMENTION':
            mentionlist.append((parno, sentno, tokenno, total_tokens, 'EMENTION'))
        elif "EMENTION" in token or "BMENTION" in token or "BQUOTE" in token or "EQUOTE" in token:
            print("Wrongly annotated quote or mention tag is causing an error: ", token, file=sys.stderr)
        else:
            tokenno += 1
            total_tokens += 1

    return quotelist, mentionlist, total_tokens


def update_tag(tagstring, tag_infolist, root):
    """Updates the sentno, begin, end attributes of a tag in the xml file"""
    # Sort quote tags to handle quotes within quotes correctly:
    if tagstring == "quote":
        sorted_quotes = []
        while tag_infolist:
            increasement = 0
            tag1, tag2 = tag_infolist[0], tag_infolist[1]
            while tag2[-1] != "EQUOTE":  # indicates quote within quote
                increasement += 2
                tag2 = tag_infolist[1+increasement]  # Obtain the right end quote-tag
            # Append tags in the right order to new quotelist
            tag2 = tag_infolist.pop(1+increasement)
            tag1 = tag_infolist.pop(0)
            sorted_quotes.append(tag1)
            sorted_quotes.append(tag2)
        tag_infolist = sorted_quotes  # Update the list with tag information to follow the correct order

    # Update each quote or mention tag with the right attributes
    for tag in root.iter(tagstring):
        btag, etag = tag_infolist.pop(0), tag_infolist.pop(0)
        tag.set('parno', str(btag[0]))
        tag.set('sentno', str(btag[1]))
        tag.set('begin', str(btag[2]))
        tag.set('end', str(btag[2] + (etag[3] - btag[3] - 1)))
        tag.set('ttokenno', str(btag[3]))


def clean_characterlist(root):
    """Collect all the speaker values from the mentions, then use
    these to clean up the character list"""
    mentioned_speakers = {mention.get('speaker') for mention in root.iter('mention')}

    # Remove all character elements that are not listed as mentioned speakers
    characters = root.find('characters')
    for character in characters:
        if character.get('name') not in mentioned_speakers:
            characters.remove(character)


def make_xml(booknlp, quotes, mentions, clusters):
    """Create an xml file with character, quote and mention tags"""
    doc = []
    quotes_df = pd.read_csv(quotes, sep='\t')
    clusters_df = pd.read_csv(clusters, sep='\t')
    mentions_df = pd.read_csv(mentions, sep='\t')
    characters_dict = create_characters_dict(quotes_df, clusters_df)
    mentions_dict = create_mentions_dict(quotes_df, mentions_df)

    with open(booknlp, 'r') as bnlp:
        # Create start of document
        doc.append('<?xml version="1.0" encoding="UTF-8"?>')
        line = '<doc><characters>'
        for i, (cluster_id, label) in enumerate(characters_dict.items()):
            line += f'<character aliases=\"{label}\" id=\"{i}\" name=\"{label}\"></character>'
        line += '</characters><text>'
        doc.append(line)

        # Create variables to store ongoing quotes, current mention end tokens,
        # token_numbers and the annotated text for the document
        ongoing = False
        current_mention_end = ""
        sentno, tokenno, total_tokenno = 0, 0, 1
        text = ""

        # Go over the lines and create <quote> and <mention> tags
        for line in bnlp:
            columns = line.split()  # Split to get the 13 BookNLP columns
            if line.startswith('#'):  # Skip lines with #
                pass
            # If it contains columns, detect quotes and mentions and add tags
            elif columns:
                token, speaker_id, iob_tag = columns[3], columns[9], columns[11]
                if ongoing and iob_tag != 'I':  # End quote tag
                    text += f'</quote>'
                    ongoing = False
                if total_tokenno in list(mentions_dict.keys()):  # Add begin of mention tag
                    speaker = characters_dict.get(str(mentions_dict[total_tokenno]['cluster']), "")
                    text += f' <mention speaker=\"{speaker}\">'
                    current_mention_end = mentions_dict[total_tokenno]['end']
                if iob_tag == 'B':  # Begin quote tag
                    text += f' <quote speaker=\"{characters_dict.get(speaker_id, "")}\">{token}'
                    ongoing = True
                elif total_tokenno in list(mentions_dict.keys()):  # No space after <mention>
                    text += f'{token}'
                else:
                    text += f' {token}'
                if total_tokenno == current_mention_end:  # End mention tag
                    text += f'</mention>'
                tokenno += 1
                total_tokenno += 1
            else:
                if text:
                    doc.append(text)
                    text = ""
                sentno += 1
                tokenno = 0
        if ongoing:
            doc.append("</quote>")
        doc.append('</text></doc>')  # End the document

        # Print all the lines
        for line in doc:
            print(line)


def update_xml(xml_file, booknlp):
    """Update the annotated xml file by adding several attributes to the
    quote- and mention tags, such as parno, sentno, start token indices etc."""
    # Create list with sentence IDs (parno-sentno values) for each sentence
    sids = []
    with open(booknlp, 'r') as f:
        for line in f:
            if line.startswith('#'):
                pass
            elif line.split() and line.split()[1] not in sids:
                sids.append(line.split()[1])  # Store sentence ID of this line

    # Update the quote- and mention attributes
    with open(xml_file, 'r') as f:
        # Check whether the amount of lines is the same as the amount of sentence IDs
        lines = [line for line in f]
        if len(lines) != len(sids):
            # Then the xml file ends with a </quote> tag, so we append this to the previous line.
            last_line = lines.pop()
            lines[-1] = lines[-1].strip() + last_line

        # For each line, we update the quotes- and mentions attributes within the tags
        quote_info, mention_info = [], []
        total_tokens = 1  # In the gold files, total tokens start from index 1
        for line in lines:
            if sids:
                parno, sentno = sids.pop(0).split("-")
                quote_info, mention_info, total_tokens = update_qm_lists(quote_info, mention_info, line, int(parno), int(sentno), total_tokens)

    # Update the quote and mention tags
    tree = ET.parse(xml_file)
    root = tree.getroot()
    update_tag('quote', quote_info, root)
    update_tag('mention', mention_info, root)
    clean_characterlist(root)
    new_name = str(os.path.splitext(xml_file)[0]) + "_updated.xml"
    tree.write(new_name, encoding="UTF-8", xml_declaration=True)


def main():
    args = create_arg_parser()
    if args.action == "create":
        make_xml(args.booknlp, args.quotes, args.mentions, args.clusters)
    elif args.action == "update":
        update_xml(args.xml, args.booknlp)


if __name__ == '__main__':
    main()
