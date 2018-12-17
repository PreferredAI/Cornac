# -*- coding: utf-8 -*-

"""
@author: Quoc-Tuan Truong <tuantq.vnu@gmail.com>
"""

import numpy as np


class BaseStrategy:

    """Base Evaluation Strategy

    Parameters
    ----------

    train_set: :obj:`TrainSet<cornac.data.TrainSet>`, optional, default: None
        The training data.

    val_set: :obj:`TestSet<cornac.data.TestSet>`, optional, default: None
        The validation data.

    test_set: :obj:`TestSet<cornac.data.TestSet>`, optional, default: None
        The test data.

    total_users: int, optional, default: None
        Total number of unique users in the data including train, val, and test sets

    total_users: int, optional, default: None
        Total number of unique items in the data including train, val, and test sets

    rating_threshold: float, optional, default: 1
        The minimum value that is considered to be a good rating used for ranking, \
        e.g, if the ratings are in {1, ..., 5}, then good_rating = 4.

    user_based: bool, optional, default: True
        Performance will be averaged based on number of users for rating metrics.
        If `False`, averaging over number of ratings will be computed.

    exclude_unknowns: bool, optional, default: False
        Ignore unknown users and items (cold-start) during evaluation and testing

    verbose: bool, optional, default: False
        Output running log
    """

    def __init__(self, train_set=None, val_set=None, test_set=None,
                 total_users=None, total_items=None, rating_threshold=1.,
                 user_based=True, exclude_unknowns=False, verbose=False):
        self.train_set = train_set
        self.val_set = val_set
        self.test_set = test_set
        self.total_users = total_users
        self.total_items = total_items
        self.rating_threshold = rating_threshold
        self.user_based = user_based
        self.exclude_unknowns = exclude_unknowns
        self.verbose = verbose

        if verbose:
            print('Rating threshold = {:.1f}'.format(rating_threshold))
            print('exclude_unknowns = {}'.format(exclude_unknowns))


    def evaluate(self, model, metrics):
        rating_metrics = metrics.get('rating', [])
        ranking_metrics = metrics.get('ranking', [])

        if self.train_set is None:
            raise ValueError('train_set is required but None!')

        if self.test_set is None:
            raise ValueError('test_set is required but None!')

        if self.total_users is None:
            self.total_users = len(set(self.train_set.get_uid_list() +
                                       self.val_set.get_uid_list() +
                                       self.test_set.get_uid_list()))

        if self.total_items is None:
            self.total_items = len(set(self.train_set.get_iid_list() +
                                       self.val_set.get_iid_list() +
                                       self.test_set.get_iid_list()))

        if self.verbose:
            print("Training started!")

        model.fit(self.train_set)

        if self.verbose:
            print("Evaluation started!")

        all_rating_gts = []
        all_rating_pds = []
        metric_user_results = {}
        for mt in (rating_metrics + ranking_metrics):
            metric_user_results[mt.name] = {}

        for i, user_id in enumerate(self.test_set.get_users()):
            if self.verbose and i % 1000 == 0:
                print(i, "users processed")

            # ignore unknown users when self.exclude_unknown
            if self.exclude_unknowns and self.train_set.is_unk_user(user_id):
                continue

            u_rating_gts = []
            u_rating_pds = []
            if self.exclude_unknowns:
                u_ranking_gts = np.zeros(self.train_set.num_items)
                candidate_item_ids = None # all known items
            else:
                u_ranking_gts = np.zeros(self.total_items)
                candidate_item_ids = range(self.total_items)

            for item_id, rating in self.test_set.get_ratings(user_id):
                # ignore unknown items when self.exclude_unknown
                if self.exclude_unknowns and self.train_set.is_unk_item(item_id):
                    continue

                if len(rating_metrics) > 0:
                    all_rating_gts.append(rating)
                    u_rating_gts.append(rating)

                    rating_pred = model.rate(user_id, item_id)
                    all_rating_pds.append(rating_pred)
                    u_rating_pds.append(rating_pred)

                # constructing ranking ground-truth
                if rating >= self.rating_threshold:
                    u_ranking_gts[item_id] = 1

            # per user evaluation for rating metrics
            if len(rating_metrics) > 0 and len(u_rating_gts) > 0:
                for mt in rating_metrics:
                    mt_score = mt.compute(np.asarray(u_rating_gts), np.asarray(u_rating_pds))
                    metric_user_results[mt.name][user_id] = mt_score

            # per user evaluation for ranking metrics
            if len(ranking_metrics) > 0 and u_ranking_gts.sum() > 0:
                u_ranking_pds = model.rank(user_id, candidate_item_ids)
                for mt in ranking_metrics:
                    mt_score = mt.compute(u_ranking_gts, u_ranking_pds)
                    metric_user_results[mt.name][user_id] = mt_score

        metric_avg_results = {}

        # avg results of rating metrics
        for mt in rating_metrics:
            if self.user_based: # averaging over users
                user_results = list(metric_user_results[mt.name].values())
                metric_avg_results[mt.name] = np.asarray(user_results).mean()
            else: # averaging over ratings
                metric_avg_results[mt.name] = mt.compute(np.asarray(all_rating_gts), np.asarray(all_rating_pds))

        # avg results of ranking metrics
        for mt in ranking_metrics:
            user_results = list(metric_user_results[mt.name].values())
            metric_avg_results[mt.name] = np.asarray(user_results).mean()

        return metric_avg_results, metric_user_results