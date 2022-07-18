# A Neural Approach to Quote Attribution in Dutch Literature
Master's thesis for the MSc Information Science at the University of Groningen.

In order to replicate our results, make sure to first clone the dutchcoref repository and install the required packages: </br>
https://github.com/andreasvc/dutchcoref.

The OpenBoek files, including our annotated quote data, will be made available in the near future: </br>
https://andreasvc.github.io/openboek/.

</br>


## Dialogue annotation
In order to train or evaluate the classifier, xml files containing the gold quotation information are needed. The following instructions are tailored to replicate the annotation of direct speech in Dutch novels.

### Creating the xml files with silver information
Converter.py can be used to convert dutchcoref's booknlp format output to xml format, adding silver information about characters, quotes and mentions.

To create the xml files, use converter.py with the "create" action. Note that gold information about mentions, quotes and clusters is required.
```bash
$ python3 converter.py -a create -b goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.conll
    -m goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.mentions.tsv
    -q goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.quotes.tsv
    -c goldfiles/Grunberg_HuidEnHaar/Grunberg_HuidEnHaar.clusters.tsv
```

The xml file containing silver information can then be corrected with the Quote Annotator tool: https://github.com/muzny/quoteannotator. </br>
Our guidelines for annotating quotes in Dutch novels can be found here: [guidelines](annotation_guidelines.pdf)

### Updating the xml files after annotating
After using the annotation tool, use converter.py with the "update" action to complete the gold xml files with information about paragraph-, sentence- and token numbers. Providing the gold output.conll file in Dutchcoref's booknlp format is required:
```bash
$ python3 converter.py -a update -x Abdolah_Koning_annotated.xml -b goldfiles/Abdolah_Koning/Abdolah_Koning.conll
```

</br>

## Classifier usage

The code and trained model files for each classifier can be found in the [models](/models) directory.

### Training and evaluating the standalone classifier

In order to get the speaker mention and cluster performance, we can run the classifiers as follows*:
```bash
$ python qaclassifier.py  -t '../riddlecoref/split/riddle/train/*.conll' -v '../riddlecoref/split/riddle/dev/*.conll' -p ../riddlecoref/parses/ -a ../riddlecoref/annotations/riddlecoref/
```

\* If the model is already trained, providing the '-e' argument will just run the evaluation, preventing the classifier from training again. 


### Quote attribution within dutchcoref
To run the quote attribution classifier implemented within dutchcoref, make sure to first place all the model files in the dutchcoref folder.
Now run the classifier as follows:
```bash
$ python3 coref_neural.py --outputprefix /tmp/Gilbert_EtenBiddenBeminnen /riddlecoref/parses/Gilbert_EtenBiddenBeminnen/ --neural=quote
```

In order to evaluate the results, we use evalquotes.py, for which gold output from the dutchcoref system is required:
```bash
$ python3 evalquotes.py /riddlecoref/annotations/riddlecoref/Gilbert_EtenBiddenBeminnen.xml /dutchcoref/tmp/Gilbert_EtenBiddenBeminnen goldfiles/Gilbert_EtenBiddenBeminnen/Gilbert_EtenBiddenBeminnen
```

</br>

## References

**Dutchcoref original paper:** </br>
van Cranenburgh, Andreas. "A Dutch coreference resolution system with an evaluation on literary fiction." Computational Linguistics in the Netherlands Journal 9 (2019): 27-54. https://clinjournal.org/clinj/article/view/91

**The Quote Annotator tool is from:** </br>
Grace Muzny, Michael Fang, Angel Fang and Dan Jurafsky. A Two-stage Sieve Approach to Quote Attribution. In Proceedings of the European Chapter of the Association for Computational Linguistics (EACL), 2017, Valencia, Spain.
