from pathlib import Path

import networkx as nx

from .annotations import AnnotationReader
from .io_helpers import read_toml
from .landmarks import LandmarkReader
from .skeletons import SkeletonReader
from .volumes import VolumeReader


class DataReader:
    """Class for reading exported data.

    Attributes
    ----------
    metadata : Optional[dict[str, Any]]
        Metadata of export, if present.
    volumes : Optional[VolumeReader]
        Reader for volume data, if present.
    landmarks : Optional[LandmarkReader]
        Reader for landmark data, if present.
    neurons : Optional[SkeletonReader]
        Reader for neuronal/ skeleton data, if present.
    annotations : Optional[AnnotationReader]
        Reader for annotation data, if present.
    """

    def __init__(self, dpath: Path) -> None:
        """
        Parameters
        ----------
        dpath : Path
            Directory in which all data is saved.
        """
        self.dpath = Path(dpath)

        meta_path = self.dpath / "metadata.toml"
        if meta_path.is_file():
            self.metadata = read_toml(meta_path)
        else:
            self.metadata = None

        self.volumes = (
            VolumeReader(dpath / "volumes") if (dpath / "volumes").is_dir() else None
        )
        self.landmarks = (
            LandmarkReader(dpath / "landmarks")
            if (dpath / "landmarks").is_dir()
            else None
        )
        self.neurons = (
            SkeletonReader(
                dpath / "neurons",
                self.metadata.get("units") if self.metadata else None,
            )
            if (dpath / "neurons").is_dir()
            else None
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
