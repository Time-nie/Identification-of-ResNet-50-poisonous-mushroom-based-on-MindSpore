# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Create train or eval dataset."""
import os
import mindspore.common.dtype as mstype
import mindspore.dataset.engine as de
import mindspore.dataset.vision.c_transforms as C
import mindspore.dataset.transforms.c_transforms as C2


def create_dataset(dataset_path, do_train, repeat_num=1, batch_size=32):
    """
    Create a train or eval dataset.

    Args:
        dataset_path (str): The path of dataset.
        do_train (bool): Whether dataset is used for train or eval.
        repeat_num (int): The repeat times of dataset. Default: 1.
        batch_size (int): The batch size of dataset. Default: 32.

    Returns:
        Dataset.
    """
    device_num, rank_id = _get_rank_info()

    if device_num == 1:
        ds = de.ImageFolderDataset(dataset_path, num_parallel_workers=8, shuffle=True)
    else:
        ds = de.ImageFolderDataset(dataset_path, num_parallel_workers=8, shuffle=True,
                                   num_shards=device_num, shard_id=rank_id)

    image_size = 224
    mean = [0.485 * 255, 0.456 * 255, 0.406 * 255]
    std = [0.229 * 255, 0.224 * 255, 0.225 * 255]

    # define map operations
    if do_train:
        trans = [
            C.RandomCropDecodeResize(image_size, scale=(0.08, 1.0), ratio=(0.75, 1.333)),
            C.RandomHorizontalFlip(prob=0.5),
            C.Normalize(mean=mean, std=std),
            C.HWC2CHW()
        ]
    else:
        trans = [
            C.Decode(),
            C.Resize(256),
            C.CenterCrop(image_size),
            C.Normalize(mean=mean, std=std),
            C.HWC2CHW()
        ]

    type_cast_op = C2.TypeCast(mstype.int32)

    ds = ds.map(operations=trans, input_columns="image", num_parallel_workers=8)
    ds = ds.map(operations=type_cast_op, input_columns="label", num_parallel_workers=8)

    # apply batch operations
    ds = ds.batch(batch_size, drop_remainder=True)

    # apply dataset repeat operation
    ds = ds.repeat(repeat_num)

    return ds


def _get_rank_info():
    """
    get rank size and rank id
    """
    rank_size = int(os.environ.get("RANK_SIZE", 1))
    rank_id = 0

    return rank_size, rank_id
