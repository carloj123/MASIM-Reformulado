class Photo:

    def __init__(self, size: int, victims: list, location: list):
        """
        [Object <Consumable> that represents a photography,
        resultant of a 'photograph' action over a flood instance.]

        :param size: Amount of virtual space that a photo instance
        costs over the virtual storage of an agent.
        :param victims: List of possible associated victims.
        :param node: Representation of the location where the photo
        instance was taken.
        """

        self.type: str = 'photo'
        self.size: int = size
        self.victims: list = victims
        self.location: list = location
        self.active: bool = False

    def json(self):
        victims = [victim.json() for victim in self.victims if victim.active]
        copy = self.__dict__.copy()
        copy['victims'] = victims
        del copy['active']
        copy['location'] = {'lat': copy['location'][0], 'lon': copy['location'][1]}
        return copy
