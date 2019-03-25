# -*- coding: utf-8 -*-

"""
@author: Quoc-Tuan Truong <tuantq.vnu@gmail.com>
"""

from . import FeatureModule
from typing import List, Dict, Callable, Union
from collections import defaultdict, Counter
import pickle
import numpy as np
import scipy.sparse as sp
import re
import string

PAD, UNK, BOS, EOS = '<PAD>', '<UNK>', '<BOS>', '<EOS>'
SPECIAL_TOKENS = [PAD, UNK, BOS, EOS]

__all__ = ['CountVectorizer']


class Tokenizer():
    """
    Generic class for other subclasses to extend from. This typically
    either splits text into word tokens or character tokens.
    """

    def tokenize(self, t: str) -> List[str]:
        """
        Splitting text into tokens.

        Returns
        -------
        tokens : ``List[str]``
        """
        raise NotImplementedError

    def batch_tokenize(self, texts: List[str]) -> List[List[str]]:
        """
        Splitting a corpus with multiple text documents.

        Returns
        -------
        tokens : ``List[List[str]]``
        """
        raise NotImplementedError


def rm_tags(t: str) -> str:
    """
    Remove html tags.
    e,g, rm_tags("<i>Hello</i> <b>World</b>!") -> "Hello World".
    """
    return re.sub('<([^>]+)>', '', t)


def rm_numeric(t: str) -> str:
    """
    Remove digits from `t`.
    """
    return re.sub('[0-9]+', ' ', t)


def rm_punctuation(t: str) -> str:
    """
    Remove "!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~" from t.
    """
    return t.translate(str.maketrans('', '', string.punctuation))


def rm_dup_spaces(t: str) -> str:
    """
    Remove duplicate spaces in `t`.
    """
    return re.sub(' {2,}', ' ', t)


DEFAULT_PRE_RULES = [lambda t: t.lower(), rm_tags, rm_numeric, rm_punctuation, rm_dup_spaces]


class BaseTokenizer(Tokenizer):
    """
    A base tokenizer use a provided delimiter `sep` to split text.
    """

    def __init__(self, sep=' ', pre_rules: List[Callable[[str], str]] = None):
        self.sep = sep
        self.pre_rules = DEFAULT_PRE_RULES if pre_rules is None else pre_rules

    def tokenize(self, t: str) -> List[str]:
        """
        Splitting text into tokens.

        Returns
        -------
        tokens : ``List[str]``
        """
        for rule in self.pre_rules:
            t = rule(t)
        tokens = t.split(self.sep)
        return tokens

    # TODO: this function can be parallelized
    def batch_tokenize(self, texts: List[str]) -> List[List[str]]:
        """
        Splitting a corpus with multiple text documents.

        Returns
        -------
        tokens : ``List[List[str]]``
        """
        return [self.tokenize(t) for t in texts]


class Vocabulary():
    """
    Vocabulary basically contains mapping between numbers and tokens and vice versa.
    """

    def __init__(self, idx2tok: List[str]):
        self.idx2tok = self._add_special_tokens(idx2tok)
        self.build_tok2idx()

    def build_tok2idx(self):
        self.tok2idx = defaultdict(int, {tok: idx for idx, tok in enumerate(self.idx2tok)})

    @staticmethod
    def _add_special_tokens(idx2tok: List[str]) -> List[str]:
        for tok in reversed(SPECIAL_TOKENS):  # <PAD>:0, '<UNK>':1, '<BOS>':2, '<EOS>':3
            if tok in idx2tok:
                idx2tok.remove(tok)
            idx2tok.insert(0, tok)
        return idx2tok

    @property
    def size(self):
        return len(self.idx2tok)

    def to_idx(self, tokens: List[str]) -> List[int]:
        """
        Convert a list of `tokens` to their integer indices.
        """
        return [self.tok2idx.get(tok, 1) for tok in tokens]  # 1 is <UNK> idx

    def to_text(self, indices: List[int], sep=' ') -> List[str]:
        """
        Convert a list of integer `indices` to their tokens.
        """
        return sep.join([self.idx2tok[i] for i in indices]) if sep is not None else [self.idx2tok[i] for i in indices]

    def save(self, path):
        """
        Save idx2tok into a pickle file.
        """
        pickle.dump(self.idx2tok, open(path, 'wb'))

    @classmethod
    def from_tokens(cls, tokens: List[str], max_vocab: int = None, min_freq: int = 1) -> 'Vocabulary':
        """
        Build a vocabulary from list of tokens.
        """
        freq = Counter(tokens)
        idx2tok = [tok for tok, cnt in freq.most_common(max_vocab) if cnt >= min_freq]
        return cls(idx2tok)

    @classmethod
    def from_sequences(cls, sequences: List[List[str]], max_vocab: int = None, min_freq: int = 1) -> 'Vocabulary':
        """
        Build a vocabulary from sequences (list of list of tokens).
        """
        return Vocabulary.from_tokens([tok for seq in sequences for tok in seq], max_vocab, min_freq)

    @classmethod
    def load(cls, path):
        """
        Load a vocabulary from `path` to a pickle file.
        """
        return cls(pickle.load(open(path, 'rb')))


# TODO: add stop_words
class CountVectorizer():
    """Convert a collection of text documents to a matrix of token counts
    This implementation produces a sparse representation of the counts using
    scipy.sparse.csr_matrix.

    Parameters
    ----------
    tokenizer: Tokenizer, optional, default = None
        Tokenizer for text splitting. If None, the BaseTokenizer will be used.

    vocab: Vocabulary, optional, default = None
        Vocabulary of tokens. It contains mapping between tokens to their
        integer ids and vice versa.

    max_doc_freq: Union[float, int] = 1.0
        The maximum frequency of tokens appearing in documents to be excluded from vocabulary.
        If float, the value represents a proportion of documents, int for absolute counts.
        If `vocab` is not None, this will be ignored.

    min_freq: int, default = 1
        The minimum frequency of tokens to be included into vocabulary.
        If `vocab` is not None, this will be ignored.

    stop_words : string {'english'}, list, default: None

    max_features : int, default=None
        If not None, build a vocabulary that only consider the top
        `max_features` ordered by term frequency across the corpus.
        If `vocab` is not None, this will be ignored.

    binary : boolean, default=False
        If True, all non zero counts are set to 1.
    """

    def __init__(self,
                 tokenizer: Tokenizer = None,
                 vocab: Vocabulary = None,
                 max_doc_freq: Union[float, int] = 1.0,
                 min_freq: int = 1,
                 stop_words: Union[str, List] = None,
                 max_features: int = None,
                 binary: bool = False):
        self.tokenizer = tokenizer
        if tokenizer is None:
            self.tokenizer = BaseTokenizer()
        self.vocab = vocab
        self.max_doc_freq = max_doc_freq
        self.min_freq = min_freq
        if max_doc_freq < 0 or min_freq < 0:
            raise ValueError("negative value for max_doc_freq or min_freq")
        self.max_features = max_features
        if max_features is not None:
            if max_features <= 0:
                raise ValueError("max_features=%r, neither a positive integer nor None" % max_features)
        self.binary = binary

    def _doc_freq(self, X: sp.csr_matrix):
        """
        Return number of documents that the terms appear.
        """
        return np.bincount(X.indices, minlength=X.shape[1])

    def _limit_features(self, X: sp.csr_matrix, max_doc_count: int):
        """Remove too common features.
        Prune features that are non zero in more samples than max_doc_count
        and modifying the vocabulary.
        """
        if max_doc_count >= X.shape[0]:
            return X

        # Calculate a mask based on document frequencies
        doc_frequencies = self._doc_freq(X)
        term_indices = np.arange(X.shape[1])  # terms are already sorted based on frequency from Vocabulary
        mask = np.ones(len(doc_frequencies), dtype=bool)
        mask &= doc_frequencies <= max_doc_count

        if self.max_features is not None and mask.sum() > self.max_features:
            mask_indices = term_indices[mask][:self.max_features]
            new_mask = np.zeros(len(doc_frequencies), dtype=bool)
            new_mask[mask_indices] = True
            mask = new_mask

        for index in np.sort(np.where(np.logical_not(mask))[0])[::-1]:
            del self.vocab.idx2tok[index + len(SPECIAL_TOKENS)]
        self.vocab.build_tok2idx()  # rebuild the mapping

        kept_indices = np.where(mask)[0]
        if len(kept_indices) == 0:
            raise ValueError("After pruning, no terms remain. Try a lower"
                             " min_freq or a higher max_doc_freq.")
        return X[:, kept_indices]

    def _count(self, sequences: List[List[str]]):
        """
        Create sparse feature matrix of document term counts
        """
        data = []
        indices = []
        indptr = [0]
        for sequence in sequences:
            feature_counter = Counter()
            for token in sequence:
                if token not in self.vocab.tok2idx.keys():
                    continue
                idx = self.vocab.tok2idx[token] - len(SPECIAL_TOKENS)  # ignore SPECIAL_TOKENS from count vectors
                feature_counter[idx] += 1

            indices.extend(feature_counter.keys())
            data.extend(feature_counter.values())
            indptr.append(len(indices))

        indices = np.asarray(indices, dtype=np.int)
        indptr = np.asarray(indptr, dtype=np.int)
        data = np.asarray(data, dtype=np.int)

        X = sp.csr_matrix((data, indices, indptr),
                          shape=(len(sequences), self.vocab.size - len(SPECIAL_TOKENS)),
                          dtype=np.int64)
        X.sort_indices()
        return X

    def fit(self, raw_documents: List[str]) -> 'CountVectorizer':
        """Build a vocabulary of all tokens in the raw documents.

        Parameters
        ----------
        raw_documents : iterable
            An iterable which yields either str, unicode or file objects.

        Returns
        -------
        self
        """
        self.fit_transform(raw_documents)
        return self

    def fit_transform(self, raw_documents: List[str]) -> (List[List[str]], sp.csr_matrix):
        """Build the vocabulary and return term-document matrix.

        Parameters
        ----------
        raw_documents : List[str]

        Returns
        -------
        (sequences, X) :
            sequences: List[List[str]
                Tokenized sequences of raw_documents
            X: array, [n_samples, n_features]
                Document-term matrix.
        """
        sequences = self.tokenizer.batch_tokenize(raw_documents)

        fixed_vocab = self.vocab is not None
        if self.vocab is None:
            self.vocab = Vocabulary.from_sequences(sequences, min_freq=self.min_freq)

        X = self._count(sequences)

        if self.binary:
            X.data.fill(1)

        if not fixed_vocab:
            n_docs = X.shape[0]
            max_doc_count = (self.max_doc_freq if isinstance(self.max_doc_freq, int)
                             else self.max_doc_freq * n_docs)
            X = self._limit_features(X, max_doc_count)

        return sequences, X

    def transform(self, raw_documents):
        """Transform documents to document-term matrix.

        Parameters
        ----------
        raw_documents : List[str]

        Returns
        -------
        (sequences, X) :
            sequences: List[List[str]
                Tokenized sequences of raw_documents.
            X: array, [n_samples, n_features]
                Document-term matrix.
        """
        sequences = self.tokenizer.batch_tokenize(raw_documents)
        X = self._count(sequences)
        if self.binary:
            X.data.fill(1)
        return sequences, X


# TODO: add stop_words
class TextModule(FeatureModule):
    """Text module

    Parameters
    ----------
    id_text: Dict, optional, default = None
        A dictionary contains mapping between user/item id to their text.

    tokenizer: Tokenizer, optional, default = None
        Tokenizer for text splitting. If None, the BaseTokenizer will be used.

    vocab: Vocabulary, optional, default = None
        Vocabulary of tokens. It contains mapping between tokens to their
        integer ids and vice versa.

    max_vocab: int, optional, default = None
        The maximum size of the vocabulary.
        If vocab is provided, this will be ignored.

    max_doc_freq: Union[float, int] = 1.0
        The maximum frequency of tokens appearing in documents to be excluded from vocabulary.
        If float, the value represents a proportion of documents, int for absolute counts.
        If `vocab` is not None, this will be ignored.

    min_freq: int, default = 1
        The minimum frequency of tokens to be included into vocabulary.
        If `vocab` is not None, this will be ignored.

    """

    def __init__(self,
                 id_text: Dict = None,
                 tokenizer: Tokenizer = None,
                 vocab: Vocabulary = None,
                 max_vocab: int = None,
                 max_doc_freq: Union[float, int] = 1.0,
                 min_freq: int = 1,
                 **kwargs):
        super().__init__(**kwargs)

        self._id_text = id_text
        self.tokenizer = tokenizer
        self.vocab = vocab
        self.max_vocab = max_vocab
        self.max_doc_freq = max_doc_freq
        self.min_freq = min_freq
        self.sequences = None
        self.counts = None

    def _build_text(self, global_id_map: Dict):
        """Build the text based on provided global id map
        """
        if self._id_text is None:
            return

        ordered_texts = []
        mapped2raw = {mapped_id: raw_id for raw_id, mapped_id in global_id_map.items()}
        for mapped_id in range(len(global_id_map)):
            raw_id = mapped2raw[mapped_id]
            ordered_texts.append(self._id_text[raw_id])
            del self._id_text[raw_id]
        del self._id_text

        vectorizer = CountVectorizer(tokenizer=self.tokenizer, vocab=self.vocab,
                                     max_doc_freq=self.max_doc_freq, min_freq=self.min_freq,
                                     stop_words=None, max_features=self.max_vocab, binary=False)
        self.sequences, self.counts = vectorizer.fit_transform(ordered_texts)
        self.vocab = vectorizer.vocab

        # Map tokens into integer ids
        for i, seq in enumerate(self.sequences):
            self.sequences[i] = self.vocab.to_idx(seq)

    def build(self, global_id_map):
        """Build the model based on provided list of ordered ids
        """
        FeatureModule.build(self, global_id_map)
        self._build_text(global_id_map)

    def batch_seq(self, batch_ids, max_length=None):
        """Return a numpy matrix of text sequences containing token ids with size=(len(batch_ids), max_length).
        If max_length=None, it will be inferred based on retrieved sequences.
        """
        if self.sequences is None:
            raise ValueError('self.sequences is required but None!')

        if max_length is None:
            max_length = max(len(self.sequences[mapped_id]) for mapped_id in batch_ids)

        seq_mat = np.zeros((len(batch_ids), max_length), dtype=np.int)
        for i, mapped_id in enumerate(batch_ids):
            idx_seq = self.sequences[mapped_id][:max_length]
            for j, idx in enumerate(idx_seq):
                seq_mat[i, j] = idx

        return seq_mat

    def batch_bow(self, batch_ids, binary=False):
        """Return matrix of bag-of-words corresponding to provided batch_ids
        """
        if self.counts is None:
            raise ValueError('self.counts is required but None!')

        bow_mat = self.counts[batch_ids]
        if binary:
            bow_mat.data.fill(1)

        return bow_mat

    def batch_tfidf(self, batch_ids):
        """Return matrix of TF-IDF features corresponding to provided batch_ids
        """
        raise NotImplementedError
