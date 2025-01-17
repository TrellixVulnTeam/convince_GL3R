"""
A :class:`~allennlp.training.trainer.Trainer` is responsible for training a
:class:`~allennlp.models.model.Model`.

Typically you might create a configuration file specifying the model and
training parameters and then use :mod:`~allennlp.commands.train`
rather than instantiating a ``Trainer`` yourself.
"""
# pylint: disable=too-many-lines

import logging
from typing import Dict, List, Union, Any

from allennlp.common import Params, Registrable
from allennlp.common.checks import ConfigurationError, check_for_gpu
from allennlp.models.model import Model

logger = logging.getLogger(__name__)


class TrainerBase(Registrable):
    """
    The base class for an AllenNLP trainer. It can do pretty much
    anything you want. Your subclass should implement ``train``
    and also probably ``from_params``.
    """
    default_implementation = "default"

    def __init__(self,
                 serialization_dir: str,
                 cuda_device: Union[int, List] = -1,
                 allocation_dict: Dict[str, int] = None) -> None:
        check_for_gpu(cuda_device)

        self._serialization_dir = serialization_dir

        # Configure GPUs:
        if not isinstance(cuda_device, int) and not isinstance(cuda_device, list):
            raise ConfigurationError("Expected an int or list for cuda_device, got {}".format(cuda_device))

        if isinstance(cuda_device, list):
            # Only enter standard multiple GPU mode (data parallel) if allocation_dict is empty
            if allocation_dict is None or len(allocation_dict) == 0:
                logger.warning(f"Data Parallel Multiple GPU support is experimental not recommended for use. "
                               "In some cases it may lead to incorrect results or undefined behavior.")
                self._multiple_gpu = True
                self._cuda_devices = cuda_device
                self._allocation_dict = None

            # Otherwise, set cuda devices and allocation dictionary
            else:
                self._multiple_gpu = False
                self._cuda_devices = cuda_device
                self._allocation_dict = allocation_dict

        else:
            assert (allocation_dict is None or len(allocation_dict) == 0), \
                "Should not specify GPU Allocation if only one GPU!"
            self._multiple_gpu = False
            self._cuda_devices = [cuda_device]
            self._allocation_dict = None

    def _move_to_gpu(self, model: Model) -> Model:
        if self._cuda_devices[0] != -1:
            return model.cuda(self._cuda_devices[0])
        else:
            return model

    def train(self) -> Dict[str, Any]:
        """
        Train a model and return the results.
        """
        raise NotImplementedError

    @classmethod
    def from_params(cls,   # type: ignore
                    params: Params,
                    serialization_dir: str,
                    recover: bool = False):
        # pylint: disable=arguments-differ
        typ3 = params.get("trainer", {}).pop("type", "default")

        if typ3 == "default":
            # Special logic to keep old from_params behavior.
            from allennlp.training.trainer import Trainer, TrainerPieces

            pieces = TrainerPieces.from_params(params, serialization_dir, recover)  # pylint: disable=no-member
            return Trainer.from_params(model=pieces.model,
                                       serialization_dir=serialization_dir,
                                       iterator=pieces.iterator,
                                       train_data=pieces.train_dataset,
                                       validation_data=pieces.validation_dataset,
                                       params=pieces.params,
                                       validation_iterator=pieces.validation_iterator)
        else:
            return TrainerBase.by_name(typ3).from_params(params, serialization_dir, recover)
