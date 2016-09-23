# -*- coding: utf-8 -*-

# other POS for ducth : https://www.simpleweb.org/~infrieks/stt/stt.html, http://lands.let.ru.nl/cgn/doc_English/topics/version_1.0/annot/pos_tagging/info.htm

import json
from rosette.api import API, DocumentParameters, MorphologyOutput
import gensim
import re


# to specify dutch -> use 'nld' ... but where ?

class RosetteApi():
    def __init__(self):
        self.key = 'e615b6920672b704c69f2261cc7f4d69'
        self.altUrl = 'https://api.rosette.com/rest/v1/'
        self.api = API(user_key=self.key, service_url=self.altUrl)

    def get_nouns(self, source_text):
        params = DocumentParameters()
        params["content"] = source_text
        result = self.api.morphology(params, MorphologyOutput.PARTS_OF_SPEECH)
        pos_tags = result['posTags']
        tokens = result['tokens']
        nouns = [tokens[i] for i in range(0, len(pos_tags) - 1) if (pos_tags[i] == 'NOUN' or pos_tags[i] == 'PROPN')]
        print "nouns=", nouns
        return result

    def get_entitiesnlinks(self, source_text):
        params = DocumentParameters()
        params["content"] = source_text
        result = self.api.entities(params)
        print(json.dumps(result['entities'], indent=2, ensure_ascii=False, sort_keys=True).encode("utf8"))
        return result


class ReportSentences(object):
    def __init__(self, report_text):
        self.text = report_text

    def __iter__(self):
        for line in re.split("[?.:]", self.text):
            yield line


class WordEmbeddings:
    def __init__(self, sentences=None, min_count=5):
        if sentences and min_count:
            self.model = gensim.models.Word2Vec(sentences, min_count=min_count, size=4 * 12, workers=4)
            self.builded = True
        else:
            self.model = gensim.models.Word2Vec(iter=1, min_count=2)
            self.builded = False

    def build(self, init_sentences):
        self.model.build_vocab(init_sentences)
        self.builded = True
        return self

    def train(self, sentences):
        self.model.train(sentences)
        return self

    def get_vocab(self):
        return self.model.vocab

    def save(self, name):
        self.model.save(name)

    def load(self, name):
        self.model = gensim.models.Word2Vec.load(name)
        return self


if __name__ == '__main__':
    myros = RosetteApi()
    # source_text = "Last month director Paul Feig announced the movie will have an all-star female cast including Kristen Wiig, Melissa McCarthy, Leslie Jones and Kate McKinnon."
    # source_text = "Patiënte is recentelijk moeilijker gaan lopen. Er zijn gehoorsveranderingen geweest, waardoor ze de tv wat harder zet. Looppatroon: patiënte loop voorzichtig en heeft geen normale pasgrootte en stapt niet uit. Dr. Neurneberg, neuroloog"
    source_text = "Anamnese -Algemeen form. MDL -Verwijzer -Huisarts Spanga, HA -Reden van komst -Moeite met ademhalen. -MDL Voorgeschiedenis -&gt; 2001 gastroscopie ivm passageklachten: geen endoscopische afwijkingen. -Overige voorgeschiedenis bypass en COPD. -Medicatie voorgeschiedenis -geen. -Allergie&#235;n en intoleranties -peniciline allergische reactie. -Intoxicatie -roken-, alcohol-. -Anamnese -sinds twee maanden last van duizeligheid. -tractus: goede conditie -Familieanamnese -1 zusje borstkanker, moeder mammacarcinoom -Sociaal - niet getrouwd -Uitslagen onderzoeken -echo abdomen: De blaas is goed gevuld, Normale uterus. -Conclusie -Geen verdenking maligniteit. -Beleid -Beleid + Aanvraag -Colonoscopie"
    result = myros.get_nouns(source_text)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True).encode("utf8"))
    result = myros.get_entitiesnlinks(source_text)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True).encode("utf8"))
