from dataclasses import dataclass


@dataclass
class RawColumn:
    """ Represents raw data, as defined in a dataset on upload """

    id_: int
    name: str
    is_text: bool
    is_binary: bool

    def __post_init__(self) -> None:
        assert isinstance(self.id_, int)
