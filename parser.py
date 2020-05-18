import string
import sys

from spacy.attrs import LOWER, POS, ENT_TYPE, IS_ALPHA
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.lang.en import English
import spacy
import numpy as np
from spacy.matcher.phrasematcher import PhraseMatcher
from spacy.tokens.doc import Doc

from db_models import *
from spacy.matcher import Matcher
from word2number import w2n
import tts

nlp = spacy.load("en_core_web_sm")

# Create our list of punctuation marks
punctuations = string.punctuation

# Create our list of stopwords
stop_words = spacy.lang.en.stop_words.STOP_WORDS

# Load English tokenizer, tagger, parser, NER and word vectors
parser = English()

token_split = []

matcher = Matcher(nlp.vocab)

t_type = None
t_zone = None
t_discount = None
t_amount = None
context = "INITIAL"


def main():
    # SLOTS: ticket attributes (type, zone, discount), ticket amount

    # QUERY: ticket attributes (type, zone, price, discount)
    # (COMPARE: ticket price by ticket type, ticket zone)
    # (GREET:)
    # GIVE INFORMATION: ticket attribute (type, zone, time, price, discount), ticket amount
    # CONFIRMATION: yes, no

    #    test_sentence = "I am 29 years old and have no children, but why do you ask?"
    test_sentence = "16"
    # test_sentence = "yes"
    # test_sentence = "i agree"
    # test_sentence = "please do"
    # test_sentence = "that's correct"
    # test_sentence = "no, i want a day ticket"
    # test_sentence = "no, what is the discount"
    # test_sentence = "i can confirm this"

    # test_sentence = "Day"
    # test_sentence = "what kind of tickets are there and how much would i need to pay for three one day tickets?"
    # test_sentence = "How much is a single fare ticket"
    # test_sentence = "How much is the student discount"
    #    test_sentence = "How much is a day ticket"
    # test_sentence = "what kind of tickets do you have and what would I need for three one day tickets"
    # test_sentence = "How much can i ride with a day ticket"
    # test_sentence = "is a day ticket or a single ticket cheaper"
    # test_sentence = "why use the day ticket"

    #    test_sentence = "what discounts do you offer"
    # test_sentence = "do you offer discounts"
    # test_sentence = "i am a student"
    # test_sentence = "a day ticket"

    test_sentence = "I'd like a single"
    #test_sentence = "what's zone number two"
    # test_sentence = "what's student"

    generate_response(test_sentence)


def generate_response(utterance):
    global t_type, t_zone, t_discount, t_zone, t_amount, context
    doc = nlp(utterance)
    for token in doc:
        print('Text: ' + token.text, 'Lemma: ' + token.lemma_ + ', Pos: ' + token.pos_ + ', Dep: ' + token.dep_,
              [child.lemma_ for child in token.children])
    confirm_hits = []
    inform_hits = []
    query_hits = []
    parse_utterance(confirm_hits, inform_hits, query_hits, doc)
    type_result = False
    discount_result = False
    zone_result = False
    for inform_hit in inform_hits:
        print("INFORM", inform_hit[1].verb, inform_hit[1].target, inform_hit[1].frame)
        if inform_hit[1].frame == "ttype":
            for res in Ticket.select().where(Ticket.synonym.in_({inform_hit[1].target, inform_hit[1].attribute})):
                t_type = res
                if type_result:
                    print("CONFLICT: types")
                    return
                type_result = True
                break
        if inform_hit[1].frame == "dtype":
            for res in Discount.select().where(
                    Discount.synonym.in_({inform_hit[1].target, inform_hit[1].attribute})):
                t_discount = res
                if discount_result:
                    print("CONFLICT: discounts")
                    return
                discount_result = True
                break
        if inform_hit[1].frame == "ztype" and context != "AMOUNT":
            for res in Zone.select().where(
                    Zone.name.in_({inform_hit[1].verb, inform_hit[1].target, inform_hit[1].attribute})):
                t_zone = res
                if zone_result:
                    print("CONFLICT: zones")
                    return
                zone_result = True
                break
        if inform_hit[1].frame == "number":
            number = None
            for token in doc:
                try:
                    number = w2n.word_to_num(token.lemma_)
                    break
                except ValueError:
                    number = None
            if number is not None:
                if context == "ZONE":
                    t_zone = number
                if context == "AMOUNT":
                    t_amount = number
                if context == "DISCOUNT":
                    if number >= 70:
                        t_discount = Discount.get(Discount.name == "Elderly")
                    if number < 21:
                        t_discount = Discount.get(Discount.name == "Minor")
        if discount_result or type_result:
            for token in inform_hit[0]["target"].subtree:
                if token.dep_ == "nummod":
                    t_amount = w2n.word_to_num(token.lemma_)
                    break
    for query_hit in query_hits:
        print("QUERY", query_hit[1].verb, query_hit[1].target, query_hit[1].query_type, query_hit[1].frame)
        if query_hit[1].frame == "atype":
            if context in {"INITIAL", "TYPE"}:
                query_hit[1].frame = "ttype"
            if context == "ZONE":
                query_hit[1].frame = "ztype"
            if context == "DISCOUNT":
                query_hit[1].frame = "dtype"

        if query_hit[1].frame == "dtype":
            filtered = query_with_filter("DISCOUNT", query_hit[0]["target"].lemma_, query_hit[0]["target"].children)
            if filtered is not None:
                return tts.speak_up(
                    "The discount for a " + filtered.name + " is " + str(100 * filtered.discount) + " percent.")
            else:
                return list_attributes("discount", Discount.select(Discount.name, Discount.discount).distinct())

        if query_hit[1].frame in {"tprice", "ttype"}:
            filtered = query_with_filter("TYPE", query_hit[0]["target"].lemma_, query_hit[0]["target"].subtree)
            if filtered is not None:
                return tts.speak_up(
                    "The base price for a zone 1 " + filtered.name + " ticket is " + ("%.2f" % filtered.price) + " €.")
            else:
                ''' TODO:
                if query_hit[1].frame == "tprice":
                    tts.speak_up("Please specify which type of ticket you want to know about")
                '''
                return list_attributes("ticket", Ticket.select(Ticket.name).distinct())

        if query_hit[1].frame in {"ztype"}:
            filtered = query_with_filter("ZONE", query_hit[0]["target"].lemma_, query_hit[0]["target"].subtree)
            if filtered is not None:
                return tts.speak_up(
                    "The increase for zone " + filtered.name + " is " + str(100 * filtered.increase) + " percent.")
            else:
                return list_attributes("zones", Zone.select(Zone.name).distinct())

    for confirm_hit in confirm_hits:
        print("CONFIRM", confirm_hit[1].target, confirm_hit[1].frame)
        if context == "DISCOUNT":
            if confirm_hit[1].frame == "yes" and t_discount is None:
                return tts.speak_up("Which discount are you eligible for?")
            if confirm_hit[1].frame == "no":
                t_discount = Discount.get(Discount.name == "No discount")
        if context == "FINISH":
            if confirm_hit[1].frame == "yes":
                context = "DONE"
                return tts.speak_up("Thank you, here's your ticket!")
            else:
                context = "INITIAL"
                return tts.speak_up("Would you like to make changes to your ticket?")

    print("Type", "\n" if t_type is None else t_type.name + "\n", "Zone",
          "\n" if t_zone is None else t_zone.name + "\n", "Discount",
          "\n" if t_discount is None else t_discount.name + "\n", "Amount",
          "\n" if t_amount is None else str(t_amount) + "\n")

    if t_type is not None and t_zone is not None and t_discount is not None and t_amount is not None:
        context = "FINISH"
        t_price = t_amount * (t_type.price * (1 - (t_discount.discount - t_zone.increase)))
        return tts.speak_up("You ordered " + str(
            t_amount) + " " + t_type.name + " ticket for zone " + t_zone.name + ". You have " + t_discount.name + (" discount" if t_discount.name != "No discount" else "") + ". The price is " + (
                                    "%.2f" % t_price) + ", please confirm.")
    else:
        if t_type is None:
            if context != "TYPE":
                context = "TYPE"
                return tts.speak_up("What kind of ticket would you like?")
        else:
            if t_zone is None and context != "ZONE":
                if context != "ZONE":
                    context = "ZONE"
                    return tts.speak_up("Which zone would you like to cover?")
            else:
                if t_discount is None and context != "DISCOUNT":
                    if context != "DISCOUNT":
                        context = "DISCOUNT"
                        return tts.speak_up("Are you eligible for any discounts?")
                else:
                    if t_amount is None and context != "AMOUNT":
                        if context != "AMOUNT":
                            context = "AMOUNT"
                            return tts.speak_up("How many tickets would you like?")


def list_attributes(attribute, results):
    response = "The " + attribute + " are "
    for res in results[:-1]:
        response += res.name + ", "
    return tts.speak_up(response[:-2] + " and " + results[-1].name + ".")


def query_with_filter(mode, target, offspring):
    query_filter = None
    if mode == "ZONE":
        base = [res.name for res in Zone.select()]
        query_filter = get_filter_zone(offspring)
    if mode == "TYPE":
        base = [res.synonym for res in Ticket.select()]
        query_filter = get_filter(offspring)
    if mode == "DISCOUNT":
        base = [res.synonym for res in Discount.select()]
        query_filter = get_filter(offspring)

    if query_filter is None and target in base:
        query_filter = target

    if query_filter is not None:
        if mode == "ZONE":
            return Zone.select().where(Zone.name == query_filter)[0]
        if mode == "TYPE":
            return Ticket.select().where(Ticket.synonym == query_filter)[0]
        if mode == "DISCOUNT":
            return Discount.select().where(Discount.synonym == query_filter)[0]
    return None


def get_filter(list):
    for child in list:
        if child.dep_ in {"compound", "amod"}:
            return child.lemma_
    return None


def get_filter_zone(list):
    for child in list:
        if child.pos_ in {"NUM"}:
            return w2n.word_to_num(child.lemma_)
    return None


def parse_utterance(confirm_hits, inform_hits, query_hits, doc):
    verbs = []
    confirm_candidates = []
    inform_candidates = []
    query_candidates = []
    for token in doc:
        if token.dep_ in {"conj", "ROOT"}:
            verbs.append(token)
            confirm_candidates.extend(build_confirm_candidate(token))
            inform_candidates.extend(build_inform_candidate(token))
            query_candidates.extend(build_query_candidate(token))

    print(confirm_candidates)
    print(inform_candidates)
    print(query_candidates)
    confirm_hits.extend(validate_candidates(confirm_candidates, "CONFIRM", {"target"}))
    inform_hits.extend(validate_candidates(inform_candidates, "INFORM", {"verb", "target"}))
    query_hits.extend(validate_candidates(query_candidates, "QUERY", {"verb", "target", "queryType"}))


def validate_candidates(candidates, mode, keys):
    hits = []
    query = None
    for candidate in candidates:
        if all(k in candidate for k in keys):
            if mode == "QUERY":
                query = QueryFrame.select().where(QueryFrame.verb == candidate["verb"].lemma_,
                                                  QueryFrame.target.in_(
                                                      {candidate["target"].lemma_, candidate["target"].text}),
                                                  QueryFrame.query_type.in_({"*", candidate["queryType"].lemma_}))
            if mode == "INFORM":
                attribute = ""
                attr_is_num = False
                if "attribute" in candidate:
                    try:
                        attribute = w2n.word_to_num(candidate["attribute"].lemma_)
                        attr_is_num = True
                    except ValueError:
                        attribute = candidate["attribute"].lemma_
                        attr_is_num = attribute.isnumeric()
                try:
                    lemma = w2n.word_to_num(candidate["verb"].lemma_)
                    verb_is_num = True
                except ValueError:
                    lemma = candidate["verb"].lemma_
                    verb_is_num = lemma.isnumeric()
                try:
                    target = w2n.word_to_num(candidate["target"].lemma_)
                    target_is_num = True
                except ValueError:
                    target = candidate["target"].lemma_
                    target_is_num = target.isnumeric()
                query = InformFrame.select().where(
                    (InformFrame.verb == lemma) | ((InformFrame.verb == "NUM") & verb_is_num),
                    (InformFrame.target.in_({target, candidate["target"].text})) | (
                            (InformFrame.target == "NUM") & target_is_num),
                    (InformFrame.attribute == attribute) | ((InformFrame.attribute == "NUM") & attr_is_num))

            if mode == "CONFIRM":
                query = ConfirmFrame.select().where(ConfirmFrame.target == candidate["target"].lemma_)

            if query is not None:
                for new_hit in query:
                    for hit in hits:
                        if hit[1].frame == new_hit.frame:
                            if (mode == "INFORM" and (hit[1].attribute == "" or hit[1].target == new_hit.target)) or (
                                    mode == "QUERY" and hit[1].query_type == "*" or hit[1].target == new_hit.target):
                                hits.remove(hit)
                    hits.append((candidate, new_hit))
    return hits


def build_confirm_candidate(root):
    targets = []
    candidates = []
    t_weights = {"neg": 0, "intj": 1, "acomp": 2, "ROOT": 3}
    targets.append((root, t_weights[root.dep_]))
    for child in root.children:
        if child.dep_ in {'cc', 'conj'} or child.pos_ == 'PUNCT':
            continue
        for gc in child.subtree:
            if gc.dep_ in t_weights:
                targets.append((gc, t_weights[gc.dep_]))

    for target in targets:
        candidates.append({"target": target[0]})
    return candidates


def build_inform_candidate(root):
    targets = []
    attributes = []
    candidates = []
    att_weights = {"compound": 1, "amod": 2, "attr": 3, "npadvmod": 4, "prep": 5, "nummod": 6}
    t_weights = {"pobj": 2, "dobj": 1, "nsubj": 3, "conj": 4, "attr": 5, "ROOT": 6, "nummod": 7, "compound": 8,
                 "nmod": 9}

    targets.append((root, t_weights[root.dep_]))

    for child in root.children:
        if child.dep_ in {'cc', 'conj'} or child.pos_ == 'PUNCT':
            continue
        for gc in child.subtree:
            if gc.dep_ in t_weights:
                targets.append((gc, t_weights[gc.dep_]))

            if gc.dep_ in att_weights:
                attributes.append((gc, att_weights[gc.dep_]))

    targets.sort(key=lambda x: x[1])
    attributes.sort(key=lambda x: x[1])
    for target in targets:
        if not attributes:
            candidates.append({"verb": root, "target": target[0]})
        for attribute in attributes:
            candidates.append({"verb": root, "target": target[0], "attribute": attribute[0]})
    return candidates


def build_query_candidate(root):
    query_types = []
    targets = []
    candidates = []

    qt_weights = {"acomp": 1, "pcomp": 2, "nsubj": 3, "det": 4, "dobj": 5, "aux": 6, "attr": 7, "advmod": 8}
    t_weights = {"pobj": 1, "dobj": 2, "nsubj": 3, "conj": 4, "attr": 5}
    for child in root.children:
        if child.dep_ in {'cc', 'conj'} or child.pos_ == 'PUNCT':
            continue
        for gc in child.subtree:
            if gc.dep_ in qt_weights:
                query_types.append((gc, qt_weights[gc.dep_]))

            if gc.dep_ in t_weights:
                targets.append((gc, t_weights[gc.dep_]))

    targets.sort(key=lambda x: x[1])
    query_types.sort(key=lambda x: x[1])
    for target in targets:
        if not query_types:
            candidates.append({"verb": root, "target": target[0]})
        for query_type in query_types:
            candidates.append({"verb": root, "target": target[0], "queryType": query_type[0]})
    return candidates

def get_context():
    return context

if __name__ == '__main__':
    main()
