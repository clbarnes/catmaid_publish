from pathlib import Path

import networkx as nx

from .annotations import AnnotationReader
from .landmarks import LandmarkReader
from .skeletons import SkeletonReader
from .volumes import VolumeReader


class DataReader:
    """Class for reading exported data.

    Attributes
    ----------
    volumes : VolumeReader
    landmarks : LandmarkReader
    neurons : SkeletonReader
    annotations : AnnotationReader
    """

    def __init__(self, dpath: Path) -> None:
        """
        Parameters
        ----------
        dpath : Path
            Directory in which all data is saved.
        """
        self.dpath = dpath

        self.volumes = (
            VolumeReader(dpath / "volumes") if (dpath / "volumes").is_dir() else None
        )
        self.landmarks = (
            LandmarkReader(dpath / "landmarks")
            if (dpath / "landmarks").is_dir()
            else None
        )
        self.neurons = (
            SkeletonReader(dpath / "neurons") if (dpath / "neurons").is_dir() else None
        )
        self.annotations = (
            AnnotationReader(dpath / "annotations")
            if (dpath / "annotations").is_dir()
            else None
        )

    def get_full_annotation_graph(self) -> nx.DiGraph:
        """Get annotation graph including meta-annotations and neurons.

        Returns
        -------
        nx.DiGraph
            Edges are from annotation name to annotation or neuron name.
            Nodes have attribute ``"type"``,
            which is either ``"annotation"`` or ``"neuron"``.
            Edges have a boolean attribute ``"meta_annotation"``
            (whether the target is an annotation).
        """
        g = nx.DiGraph()
        if self.annotations:
            g.update(self.annotations.get_graph())
        if self.neurons:
            g.update(self.neurons.get_annotation_graph())
        return g
