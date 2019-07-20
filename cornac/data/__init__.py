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

from .modality import Modality
from .modality import FeatureModality
from .text import TextModality
from .image import ImageModality
from .graph import GraphModality
from .sentiment import SentimentModality
from .trainset import TrainSet
from .trainset import MatrixTrainSet
from .trainset import MultimodalTrainSet
from .testset import TestSet
from .testset import MultimodalTestSet
from .reader import Reader

__all__ = ['FeatureModality',
           'TextModality',
           'ImageModality',
           'GraphModality',
           'SentimentModality',
           'TrainSet',
           'MatrixTrainSet',
           'MultimodalTrainSet',
           'TestSet',
           'MultimodalTestSet',
           'Reader']
