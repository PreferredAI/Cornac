# Copyright 2018 The Cornac Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

from . import Modality
from collections import OrderedDict

class SentimentModality(Modality):
    """Aspect module
    Parameters
    ----------
    data: List[str], required
        A triplet list of user, item, and sentiment information which also a triplet list of aspect, opinion, and sentiment, \
        e.g., data=[('user1', 'item1', [('aspect1', 'opinion1', 'sentiment1')])].
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raw_data = kwargs.get('data', None)

    @property
    def sentiment(self):
        return self.__sentiment

    @sentiment.setter
    def sentiment(self, input_sentiment):
        self.__sentiment = input_sentiment

    @property
    def num_aspects(self):
        """Return the number of aspects"""
        return len(self.aspect_id_map)

    @property
    def num_opinions(self):
        """Return the number of aspects"""
        return len(self.opinion_id_map)

    @property
    def user_sentiment(self):
        return self.__user_sentiment

    @user_sentiment.setter
    def user_sentiment(self, input_user_sentiment):
        self.__user_sentiment = input_user_sentiment

    @property
    def item_sentiment(self):
        return self.__item_sentiment

    @item_sentiment.setter
    def item_sentiment(self, input_item_sentiment):
        self.__item_sentiment = input_item_sentiment

    @property
    def aspect_id_map(self):
        return self.__aspect_id_map

    @aspect_id_map.setter
    def aspect_id_map(self, input_aspect_id_map):
        self.__aspect_id_map = input_aspect_id_map

    @property
    def opinion_id_map(self):
        return self.__opinion_id_map

    @opinion_id_map.setter
    def opinion_id_map(self, input_opinion_id_map):
        self.__opinion_id_map = input_opinion_id_map

    def _build_sentiment(self, uid_map, iid_map):
        self.user_sentiment = OrderedDict()
        self.item_sentiment = OrderedDict()
        aspect_id_map = OrderedDict()
        opinion_id_map = OrderedDict()
        sentiment = OrderedDict()
        for idx, (raw_uid, raw_iid, sentiment_tuples) in enumerate(self.raw_data):
            new_uid = uid_map.get(raw_uid, None)
            new_iid = iid_map.get(raw_iid, None)
            if new_uid is None or new_iid is None:
                continue
            if new_uid not in self.user_sentiment:
                self.user_sentiment[new_uid] = OrderedDict()
            self.user_sentiment[new_uid][new_iid] = idx
            if new_iid not in self.item_sentiment:
                self.item_sentiment[new_iid] = OrderedDict()
            self.item_sentiment[new_iid][new_uid] = idx

            mapped_sentiment_tupples = []
            for tup in sentiment_tuples:
                aspect = tup[0]
                opinion = tup[1]
                sentiment_polarity = float(tup[2])
                mapped_aspect_id = aspect_id_map.setdefault(aspect, len(aspect_id_map))
                mapped_opinion_id = opinion_id_map.setdefault(opinion, len(opinion_id_map))
                mapped_sentiment_tupples.append((mapped_aspect_id, mapped_opinion_id, sentiment_polarity))
            sentiment.setdefault(idx, mapped_sentiment_tupples)

        self.sentiment = sentiment
        self.aspect_id_map = aspect_id_map
        self.opinion_id_map = opinion_id_map

    def build(self, uid_map=None, iid_map=None):
        """Build the model based on provided list of ordered ids
        """
        if uid_map is not None and iid_map is not None:
            self._build_sentiment(uid_map, iid_map)
        return self
