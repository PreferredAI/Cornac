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


import cornac
from cornac.eval_methods import RatioSplit
from cornac.datasets import amazon_clothing
from cornac.data import Reader

ratio_split = RatioSplit(data=amazon_clothing.load_rating(Reader(bin_threshold=1.0)),
                         test_size=0.2, rating_threshold=1.0, seed=123,
                         exclude_unknowns=True, verbose=True)

neumf = cornac.models.NeuMF(num_factors=8, layers=[16, 8], act_fn='tanh', learner='adam',
                            num_epochs=10, batch_size=256, lr=0.001, seed=123)

ndcg_50 = cornac.metrics.NDCG(k=50)
rec_50 = cornac.metrics.Recall(k=50)

cornac.Experiment(eval_method=ratio_split,
                  models=[neumf],
                  metrics=[ndcg_50, rec_50]).run()
