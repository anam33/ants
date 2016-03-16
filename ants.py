"""The ants module implements game logic for Ants Vs. SomeBees."""

import random
import sys
from ucb import main, interact, trace
from collections import OrderedDict


################
# Core Classes #
################

class Place(object):
    """A Place holds insects and has an exit to another Place."""

    def __init__(self, name, exit=None):
        """Create a Place with the given exit.

        name -- A string; the name of this Place.
        exit -- The Place reached by exiting this Place (may be None).
        """
        self.name = name
        self.exit = exit
        self.bees = []        # A list of Bees
        self.ant = None       # An Ant
        self.entrance = None  # A Place
        # Phase 1: Add an entrance to the exit
        # BEGIN Problem 2
        if self.exit:
            exit.entrance=self
        # END Problem 2

    def add_insect(self, insect):
        """Add an Insect to this Place.

        There can be at most one Ant in a Place, unless exactly one of them is
        a BodyguardAnt (Phase 4), in which case there can be two. If add_insect
        tries to add more Ants than is allowed, an assertion error is raised.

        There can be any number of Bees in a Place.
        """
        if insect.is_ant:
            if self.ant is None:
                self.ant = insect
            else:
                # Phase 4: Special handling for BodyguardAnt
                # BEGIN Problem 7
                # check if the ant in place is a container or if insect is a container
                # if either case is true, add insect to the space
                if self.ant.can_contain(insect):
                    self.ant.contain_ant(insect)
                elif insect.can_contain(self.ant):
                    insect.ant=self.ant
                    self.ant=insect
                else:
                    assert self.ant is None, 'Two ants in {0}'.format(self)
                # END Problem 7
        else:
            self.bees.append(insect)
        insect.place = self

    def remove_insect(self, insect):
        """Remove an Insect from this Place.

        A target Ant may either be directly in the Place, or be contained by a
        container Ant at this place. The true QueenAnt may not be removed. If
        remove_insect tries to remove an Ant that is not anywhere in this
        Place, an AssertionError is raised.

        A Bee is just removed from the list of Bees.
        """
        if insect.is_ant:
            # Phase 4: Special Handling for BodyguardAnt and QueenAnt
            if self.ant is insect:
                if hasattr(self.ant, 'container') and self.ant.container:
                    self.ant = self.ant.ant
                # if the ant at space is an OG queen, do not remove it
                elif isinstance(self.ant, QueenAnt):
                    if self.ant.OG:
                        return 
                    else:
                        self.ant = None
                else:
                    self.ant = None
            else:
                if hasattr(self.ant, 'container') and self.ant.container and self.ant.ant is insect:
                    #if the ant in the container is an OG queen, do not remove it
                    if isinstance(self.ant.ant, QueenAnt):
                        if self.ant.ant.OG:
                            return
                        else:
                            self.ant.ant = None
                    else:
                        self.ant.ant = None
                else:
                    assert False, '{0} is not in {1}'.format(insect, self)
        else:
            self.bees.remove(insect)

        insect.place = None

    def __str__(self):
        return self.name


class Insect(object):
    """An Insect, the base class of Ant and Bee, has armor and a Place."""

    is_ant = False
    damage = 0
    watersafe=False

    def __init__(self, armor, place=None):
        """Create an Insect with an armor amount and a starting Place."""
        self.armor = armor
        self.place = place  # set by Place.add_insect and Place.remove_insect

    def reduce_armor(self, amount):
        """Reduce armor by amount, and remove the insect from its place if it
        has no armor remaining.

        >>> test_insect = Insect(5)
        >>> test_insect.reduce_armor(2)
        >>> test_insect.armor
        3
        """
        self.armor -= amount
        if self.armor <= 0:
            self.place.remove_insect(self)

    def action(self, colony):
        """The action performed each turn.

        colony -- The AntColony, used to access game state information.
        """

    def __repr__(self):
        cname = type(self).__name__
        return '{0}({1}, {2})'.format(cname, self.armor, self.place)


class Bee(Insect):
    """A Bee moves from place to place, following exits and stinging ants."""

    name = 'Bee'
    damage = 1
    watersafe=True

    def sting(self, ant):
        """Attack an Ant, reducing the Ant's armor by 1."""
        ant.reduce_armor(self.damage)

    def move_to(self, place):
        """Move from the Bee's current Place to a new Place."""
        self.place.remove_insect(self)
        place.add_insect(self)

    def blocked(self):
        """Return True if this Bee cannot advance to the next Place."""
        # Phase 3: Special handling for NinjaAnt
        # BEGIN Problem 6A
        #blocked variable indicates if a bee can go to the next place
        #return whether there is an ant, and if so whether blocked is true or false
        if self.place.ant is None:
            return False
        return self.place.ant.blocks_path
        # END Problem 6A

    def action(self, colony):
        """A Bee's action stings the Ant that blocks its exit if it is blocked,
        or moves to the exit of its current place otherwise.

        colony -- The AntColony, used to access game state information.
        """
        if self.blocked():
            self.sting(self.place.ant)
        elif self.armor > 0 and self.place.exit is not None:
            self.move_to(self.place.exit)


class Ant(Insect):
    """An Ant occupies a place and does work for the colony."""

    is_ant = True
    implemented = False  # Only implemented Ant classes should be instantiated
    food_cost = 0
    blocks_path=True
    container=False

    def __init__(self, armor=1):
        """Create an Ant with an armor quantity."""
        Insect.__init__(self, armor)

    def can_contain(self,other):
        return self.container and self.ant==None and not other.container

class HarvesterAnt(Ant):
    """HarvesterAnt produces 1 additional food per turn for the colony."""

    name = 'Harvester'
    implemented = True
    food_cost=2

    def action(self, colony):
        """Produce 1 additional food for the colony.

        colony -- The AntColony, used to access game state information.
        """
        # BEGIN Problem 1
        #harvester produces 1 food per turn
        colony.food+=1
        # END Problem 1


class ThrowerAnt(Ant):
    """ThrowerAnt throws a leaf each turn at the nearest Bee in its range."""

    name = 'Thrower'
    implemented = True
    damage = 1
    food_cost=4
    min_range=0
    max_range=10
    def nearest_bee(self, hive):
        """Return the nearest Bee in a Place that is not the Hive, connected to
        the ThrowerAnt's Place by following entrances.

        This method returns None if there is no such Bee (or none in range).
        """
        # BEGIN Problem 3B
        #begining with place of ThrowerAnt, check if there is an any in spots in front of it within a range
        #if there is an ant for said condition, attack random bee(may be multiple in a place) or else None
        spot=self.place
        distance=0
        while spot != hive or spot.entrance!=None:
            if random_or_none(spot.bees) != None: 
                if distance in range(self.min_range,self.max_range):
                    return random_or_none(spot.bees)
            distance+=1
            spot=spot.entrance
        # END Problem 3B

    def throw_at(self, target):
        """Throw a leaf at the target Bee, reducing its armor."""
        if target is not None:
            target.reduce_armor(self.damage)

    def action(self, colony):
        """Throw a leaf at the nearest Bee in range."""
        self.throw_at(self.nearest_bee(colony.hive))

def random_or_none(s):
    """Return a random element of sequence s, or return None if s is empty."""
    if s:
        return random.choice(s)


##############
# Extensions #
##############

class Water(Place):
    """Water is a place that can only hold 'watersafe' insects."""

    def add_insect(self, insect):
        """Add insect if it is watersafe, otherwise reduce its armor to 0."""
        # BEGIN Problem 3A
        #check if insect placed waterwafe, if not reduce armor to 0
        Place.add_insect(self,insect)
        if insect.watersafe==False:
            insect.reduce_armor(insect.armor)
        # END Problem 3A


class FireAnt(Ant):
    """FireAnt cooks any Bee in its Place when it expires."""

    name = 'Fire'
    damage = 3
    # BEGIN Problem 4A
    food_cost=6
    implemented = True  # Change to True to view in the GUI
    # END Problem 4A

    def reduce_armor(self, amount):
        # BEGIN Problem 4A
        #if the amount of damage FireAnt takes will kill it
        #first,damage all bees on the same place as the FireAnt by damage
        #then, kill FireAnt RIP
        if self.armor-amount<=0:
            for pest in self.place.bees[:]:
                pest.reduce_armor(self.damage)
        Ant.reduce_armor(self,amount)
        # END Problem 4A


class LongThrower(ThrowerAnt):
    """A ThrowerAnt that only throws leaves at Bees at least 5 places away."""

    name = 'Long'
    # BEGIN Problem 4B
    food_cost=2
    #LongThrower has a minimum range and the maximum is length of the board
    min_range=5
    implemented = True  # Change to True to view in the GUI
    # END Problem 4B


class ShortThrower(ThrowerAnt):
    """A ThrowerAnt that only throws leaves at Bees at most 3 places away."""

    name = 'Short'
    # BEGIN Problem 4B
    food_cost=2
    #range has max of 4 and uses default min of 0
    max_range=4
    implemented = True   # Change to True to view in the GUI
    # END Problem 4B


# BEGIN Problem 5A
# The WallAnt class
# This Ant has not actions and just has high armor
class WallAnt(Ant):
    name='Wall'
    food_cost=4
    armor=4
    def __init__(self, armor=4):
        """Create an Ant with an armor quantity."""
        Ant.__init__(self, armor)
# END Problem 5A


class NinjaAnt(Ant):
    """NinjaAnt does not block the path and damages all bees in its place."""

    name = 'Ninja'
    damage = 1
    # BEGIN Problem 6A
    food_cost=6
    #ninja ant hides in shadows, bees can fly through shadows
    blocks_path=False
    implemented = True   # Change to True to view in the GUI
    # END Problem 6A

    def action(self, colony):
        # BEGIN Problem 6A
        #attacks every bee that comes through its location(including multiple at a time)
        for pest in self.place.bees[:]:
            pest.reduce_armor(self.damage)
        # END Problem 6A


# BEGIN Problem 5B
# The ScubaThrower class
#who lives in a pineapple under the sea?
#Sponge Bob Square (p)ANTS
#class of a ThrowerAnt that is watersafe
class ScubaThrower(ThrowerAnt):
    name='Scuba'
    food_cost=5
    implemented=True
    watersafe=True
# END Problem 5B


class HungryAnt(Ant):
    """HungryAnt will take three turns to digest a Bee in its place.
    While digesting, the HungryAnt can't eat another Bee.
    """
    name = 'Hungry'
    # BEGIN Problem 6B
    #set time to digest a bee
    time_to_digest=3
    food_cost=4
    implemented = True   # Change to True to view in the GUI
    # END Problem 6B

    def __init__(self):
        # BEGIN Problem 6B
        #initialize from super class, add digesting instance attribute
        Ant.__init__(self)
        self.digesting=0
        # END Problem 6B

    def eat_bee(self, bee):
        # BEGIN Problem 6B
        # do bees taste like honey?
        # kills bee instantly, set the timer for digesting
        bee.reduce_armor(bee.armor)
        self.digesting=self.time_to_digest
        # END Problem 6B

    def action(self, colony):
        # BEGIN Problem 6B
        #if there is a bee to eat and done digesting, eat the bee
        if self.digesting <= 0 and random_or_none(self.place.bees):
                self.eat_bee(random_or_none(self.place.bees))
        else:
        #still digesting
            self.digesting-=1
        # END Problem 6B


class BodyguardAnt(Ant):
    """BodyguardAnt provides protection to other Ants."""
    name = 'Bodyguard'
    # BEGIN Problem 7
    # a container that has no ant in it(when created)
    food_cost=4
    container=True
    implemented = True   # Change to True to view in the GUI
    # END Problem 7

    def __init__(self):
        Ant.__init__(self, 2)
        self.ant = None  # The Ant hidden in this bodyguard

    def contain_ant(self, ant):
        # BEGIN Problem 7
        #yay a new friend. change ant instance attribute to new friend
        self.ant=ant# The ScubaThrower class
        # END Problem 7

    def action(self, colony):
        # BEGIN Problem 7
        #if there is an ant, 
        if self.ant:
            self.ant.action(colony)
        # END Problem 7

class TankAnt(BodyguardAnt):
    """TankAnt provides both offensive and defensive capabilities."""
    name = 'Tank'
    damage = 1
    # BEGIN Problem 8
    food_cost=6
    implemented = True   # Change to True to view in the GUI
    # END Problem 8

    def action(self, colony):
        # BEGIN Problem 8
        #carry out action of ant in container and own action of attacking bee in place
        if self.ant:
            self.ant.action(colony)
        for pest in self.place.bees[:]:
            pest.reduce_armor(self.damage)
        # END Problem 8

class QueenAnt(ScubaThrower):
    """The Queen of the colony.  The game is over if a bee enters her place."""

    name = 'Queen'
    # BEGIN Problem 9
    num_queens=0 #how many queens are there? should only be 1
    food_cost=6
    dbld=[] #list of ants already doubled
    implemented = True   # Change to True to view in the GUI
    # END Problem 9

    def __init__(self):
        # BEGIN Problem 9
        ScubaThrower.__init__(self,1)
        #if there is no other queen, it is OG. if there is another one, it is a poser
        if self.num_queens==0:
            self.OG=True
            QueenAnt.num_queens=1
        else:
            self.OG=False
        # END Problem 9

    def action(self, colony):
        """A queen ant throws a leaf, but also doubles the damage of ants
        in her tunnel.

        Impostor queens do only one thing: reduce their own armor to 0.
        """
        # BEGIN Problem 9
        if self.OG:
            #carryout normcal action of thrower ant
            ScubaThrower.action(self,colony)
            #start from place of the queen and work backwards(forward from POV of bees) to find ants
            spot=self.place.exit
            while spot.exit!=None:
                if spot.ant!=None:
                    #if there is a container, double its damage and add to dbld
                    #also check if there is an ant in container and double its damage and add to dbld
                    if spot.ant.container:
                        if spot.ant not in self.dbld:
                            spot.ant.damage*=2
                            self.dbld=self.dbld+[spot.ant]
                        if spot.ant.ant not in self.dbld and spot.ant.ant:
                            spot.ant.ant.damage*=2
                            self.dbld=self.dbld+[spot.ant.ant]
                    else:
                    #if the ant is not already in dbld, double its damage and add it to the list
                        if spot.ant not in self.dbld:
                            spot.ant.damage*=2
                            self.dbld=self.dbld+[spot.ant]
                spot=spot.exit
        else:
            #there can only be one OG queen
            self.reduce_armor(1)
        # END Problem 9

    def reduce_armor(self, amount):
        """Reduce armor by amount, and if the True QueenAnt has no armor
        remaining, signal the end of the game.
        """
        # BEGIN Problem 9
        #bees win if the amount of armor lost for an OG queen is greater than the armor it has
        if self.armor-amount<=0 and self.OG:
            bees_win()
        else:
            Ant.reduce_armor(self,amount)
        # END Problem 9

class AntRemover(Ant):
    """Allows the player to remove ants from the board in the GUI."""

    name = 'Remover'
    implemented = False

    def __init__(self):
        Ant.__init__(self, 0)


##################
# Status Effects #
##################

def make_slow(action):
    """Return a new action method that calls action every other turn.

    action -- An action method of some Bee
    """
    # BEGIN Problem EC
    #only do the action on even times
    def delay(colony):
        if colony.time%2==0:
            action(colony)
    return delay
    # END Problem EC

def make_stun(action):
    """Return a new action method that does nothing.

    action -- An action method of some Bee
    """
    # BEGIN Problem EC
    #your turn has been skipped
    def stuck(colony):
        pass
    return stuck
    # END Problem EC

def apply_effect(effect, bee, duration):
    """Apply a status effect to a Bee that lasts for duration turns."""
    # BEGIN Problem EC
    #for an effected bee, within a duration, its actions are effected
    #change bees actions to this new set of actions
    new=effect(bee.action)
    old=bee.action
    def handicapped(colony):
        nonlocal duration
        if duration>0:
            new(colony)
        else:
            old(colony)
        duration-=1
    bee.action=handicapped
    # END Problem EC


class SlowThrower(ThrowerAnt):
    """ThrowerAnt that causes Slow on Bees."""

    name = 'Slow'
    # BEGIN Problem EC
    food_cost=4
    implemented = True   # Change to True to view in the GUI
    # END Problem EC

    def throw_at(self, target):
        if target:
            apply_effect(make_slow, target, 3)


class StunThrower(ThrowerAnt):
    """ThrowerAnt that causes Stun on Bees."""

    name = 'Stun'
    # BEGIN Problem EC
    food_cost=6
    implemented = True   # Change to True to view in the GUI
    # END Problem EC

    def throw_at(self, target):
        if target:
            apply_effect(make_stun, target, 1)


##################
# Bees Extension #
##################

class Wasp(Bee):
    """Class of Bee that has higher damage."""
    name = 'Wasp'
    damage = 2

class Hornet(Bee):
    """Class of bee that is capable of taking two actions per turn, although
    its overall damage output is lower. Immune to status effects.
    """
    name = 'Hornet'
    damage = 0.25

    def action(self, colony):
        for i in range(2):
            if self.armor > 0:
                super().action(colony)

    def __setattr__(self, name, value):
        if name != 'action':
            object.__setattr__(self, name, value)

class NinjaBee(Bee):
    """A Bee that cannot be blocked. Is capable of moving past all defenses to
    assassinate the Queen.
    """
    name = 'NinjaBee'

    def blocked(self):
        return False

class Boss(Wasp, Hornet):
    """The leader of the bees. Combines the high damage of the Wasp along with
    status effect immunity of Hornets. Damage to the boss is capped up to 8
    damage by a single attack.
    """
    name = 'Boss'
    damage_cap = 8
    action = Wasp.action

    def reduce_armor(self, amount):
        super().reduce_armor(self.damage_modifier(amount))

    def damage_modifier(self, amount):
        return amount * self.damage_cap/(self.damage_cap + amount)

class Hive(Place):
    """The Place from which the Bees launch their assault.

    assault_plan -- An AssaultPlan; when & where bees enter the colony.
    """

    def __init__(self, assault_plan):
        self.name = 'Hive'
        self.assault_plan = assault_plan
        self.bees = []
        for bee in assault_plan.all_bees:
            self.add_insect(bee)
        # The following attributes are always None for a Hive
        self.entrance = None
        self.ant = None
        self.exit = None

    def strategy(self, colony):
        exits = [p for p in colony.places.values() if p.entrance is self]
        for bee in self.assault_plan.get(colony.time, []):
            bee.move_to(random.choice(exits))
            colony.active_bees.append(bee)


class AntColony(object):
    """An ant collective that manages global game state and simulates time.

    Attributes:
    time -- elapsed time
    food -- the colony's available food total
    queen -- the place where the queen resides
    places -- A list of all places in the colony (including a Hive)
    bee_entrances -- A list of places that bees can enter
    """

    def __init__(self, strategy, hive, ant_types, create_places, dimensions, food=2):
        """Create an AntColony for simulating a game.

        Arguments:
        strategy -- a function to deploy ants to places
        hive -- a Hive full of bees
        ant_types -- a list of ant constructors
        create_places -- a function that creates the set of places
        dimensions -- a pair containing the dimensions of the game layout
        """
        self.time = 0
        self.food = food
        self.strategy = strategy
        self.hive = hive
        self.ant_types = OrderedDict((a.name, a) for a in ant_types)
        self.dimensions = dimensions
        self.active_bees = []
        self.configure(hive, create_places)

    def configure(self, hive, create_places):
        """Configure the places in the colony."""
        self.queen = QueenPlace('AntQueen')
        self.places = OrderedDict()
        self.bee_entrances = []
        def register_place(place, is_bee_entrance):
            self.places[place.name] = place
            if is_bee_entrance:
                place.entrance = hive
                self.bee_entrances.append(place)
        register_place(self.hive, False)
        create_places(self.queen, register_place, self.dimensions[0], self.dimensions[1])

    def simulate(self):
        """Simulate an attack on the ant colony (i.e., play the game)."""
        num_bees = len(self.bees)
        try:
            while True:
                self.hive.strategy(self)            # Bees invade
                self.strategy(self)                 # Ants deploy
                for ant in self.ants:               # Ants take actions
                    if ant.armor > 0:
                        ant.action(self)
                for bee in self.active_bees[:]:     # Bees take actions
                    if bee.armor > 0:
                        bee.action(self)
                    if bee.armor <= 0:
                        num_bees -= 1
                        self.active_bees.remove(bee)
                if num_bees == 0:
                    raise AntsWinException()
                self.time += 1
        except AntsWinException:
            print('All bees are vanquished. You win!')
            return True
        except BeesWinException:
            print('The ant queen has perished. Please try again.')
            return False

    def deploy_ant(self, place_name, ant_type_name):
        """Place an ant if enough food is available.

        This method is called by the current strategy to deploy ants.
        """
        constructor = self.ant_types[ant_type_name]
        if self.food < constructor.food_cost:
            print('Not enough food remains to place ' + ant_type_name)
        else:
            ant = constructor()
            self.places[place_name].add_insect(ant)
            self.food -= constructor.food_cost
            return ant

    def remove_ant(self, place_name):
        """Remove an Ant from the Colony."""
        place = self.places[place_name]
        if place.ant is not None:
            place.remove_insect(place.ant)

    @property
    def ants(self):
        return [p.ant for p in self.places.values() if p.ant is not None]

    @property
    def bees(self):
        return [b for p in self.places.values() for b in p.bees]

    @property
    def insects(self):
        return self.ants + self.bees

    def __str__(self):
        status = ' (Food: {0}, Time: {1})'.format(self.food, self.time)
        return str([str(i) for i in self.ants + self.bees]) + status

class QueenPlace(Place):
    """QueenPlace at the end of the tunnel, where the queen resides."""

    def add_insect(self, insect):
        """Add an Insect to this Place.

        Can't actually add Ants to a QueenPlace. However, if a Bee attempts to
        enter the QueenPlace, a BeesWinException is raised, signaling the end
        of a game.
        """
        assert not insect.is_ant, 'Cannot add {0} to QueenPlace'
        raise BeesWinException()

def ants_win():
    """Signal that Ants win."""
    raise AntsWinException()

def bees_win():
    """Signal that Bees win."""
    raise BeesWinException()

def ant_types():
    """Return a list of all implemented Ant classes."""
    all_ant_types = []
    new_types = [Ant]
    while new_types:
        new_types = [t for c in new_types for t in c.__subclasses__()]
        all_ant_types.extend(new_types)
    return [t for t in all_ant_types if t.implemented]

class GameOverException(Exception):
    """Base game over Exception."""
    pass

class AntsWinException(GameOverException):
    """Exception to signal that the ants win."""
    pass

class BeesWinException(GameOverException):
    """Exception to signal that the bees win."""
    pass

def interactive_strategy(colony):
    """A strategy that starts an interactive session and lets the user make
    changes to the colony.

    For example, one might deploy a ThrowerAnt to the first tunnel by invoking
    colony.deploy_ant('tunnel_0_0', 'Thrower')
    """
    print('colony: ' + str(colony))
    msg = '<Control>-D (<Control>-Z <Enter> on Windows) completes a turn.\n'
    interact(msg)

def start_with_strategy(args, strategy):
    """Reads command-line arguments and starts a game with those options."""
    import argparse
    parser = argparse.ArgumentParser(description="Play Ants vs. SomeBees")
    parser.add_argument('-d', type=str, metavar='DIFFICULTY',
                        help='sets difficulty of game (easy/medium/hard/insane)')
    parser.add_argument('-w', '--water', action='store_true',
                        help='loads a full layout with water')
    parser.add_argument('--food', type=int,
                        help='number of food to start with when testing', default=2)
    args = parser.parse_args()

    assault_plan = make_test_assault_plan()
    layout = dry_layout
    tunnel_length = 9
    num_tunnels = 1
    food = args.food

    if args.water:
        layout = wet_layout
    if args.d in ['e', 'easy']:
        assault_plan = make_easy_assault_plan()
        num_tunnels = 2
        food = 2
    elif args.d in ['n', 'normal']:
        assault_plan = make_normal_assault_plan()
        num_tunnels = 3
        food = 2
    elif args.d in ['h', 'hard']:
        assault_plan = make_hard_assault_plan()
        num_tunnels = 4
        food = 2
    elif args.d in ['i', 'insane']:
        assault_plan = make_insane_assault_plan()
        num_tunnels = 4
        food = 2

    hive = Hive(assault_plan)
    dimensions = (num_tunnels, tunnel_length)
    return AntColony(strategy, hive, ant_types(), layout, dimensions, food).simulate()


###########
# Layouts #
###########

def wet_layout(queen, register_place, tunnels=3, length=9, moat_frequency=3):
    """Register a mix of wet and and dry places."""
    for tunnel in range(tunnels):
        exit = queen
        for step in range(length):
            if moat_frequency != 0 and (step + 1) % moat_frequency == 0:
                exit = Water('water_{0}_{1}'.format(tunnel, step), exit)
            else:
                exit = Place('tunnel_{0}_{1}'.format(tunnel, step), exit)
            register_place(exit, step == length - 1)

def dry_layout(queen, register_place, tunnels=3, length=9):
    """Register dry tunnels."""
    wet_layout(queen, register_place, tunnels, length, 0)


#################
# Assault Plans #
#################

class AssaultPlan(dict):
    """The Bees' plan of attack for the Colony.  Attacks come in timed waves.

    An AssaultPlan is a dictionary from times (int) to waves (list of Bees).

    >>> AssaultPlan().add_wave(4, 2)
    {4: [Bee(3, None), Bee(3, None)]}
    """

    def add_wave(self, bee_type, bee_armor, time, count):
        """Add a wave at time with count Bees that have the specified armor."""
        bees = [bee_type(bee_armor) for _ in range(count)]
        self.setdefault(time, []).extend(bees)
        return self

    @property
    def all_bees(self):
        """Place all Bees in the hive and return the list of Bees."""
        return [bee for wave in self.values() for bee in wave]

def make_test_assault_plan():
    return AssaultPlan().add_wave(Bee, 3, 2, 1).add_wave(Bee, 3, 3, 1)

def make_easy_assault_plan():
    plan = AssaultPlan()
    for time in range(3, 16, 2):
        plan.add_wave(Bee, 3, time, 1)
    plan.add_wave(Wasp, 3, 4, 1)
    plan.add_wave(NinjaBee, 3, 8, 1)
    plan.add_wave(Hornet, 3, 12, 1)
    plan.add_wave(Boss, 15, 16, 1)
    return plan

def make_normal_assault_plan():
    plan = AssaultPlan()
    for time in range(3, 16, 2):
        plan.add_wave(Bee, 3, time, 2)
    plan.add_wave(Wasp, 3, 4, 1)
    plan.add_wave(NinjaBee, 3, 8, 1)
    plan.add_wave(Hornet, 3, 12, 1)
    plan.add_wave(Wasp, 3, 16, 1)

    #Boss Stage
    for time in range(21, 30, 2):
        plan.add_wave(Bee, 3, time, 2)
    plan.add_wave(Wasp, 3, 22, 2)
    plan.add_wave(Hornet, 3, 24, 2)
    plan.add_wave(NinjaBee, 3, 26, 2)
    plan.add_wave(Hornet, 3, 28, 2)
    plan.add_wave(Boss, 20, 30, 1)
    return plan

def make_hard_assault_plan():
    plan = AssaultPlan()
    for time in range(3, 16, 2):
        plan.add_wave(Bee, 4, time, 2)
    plan.add_wave(Hornet, 4, 4, 2)
    plan.add_wave(Wasp, 4, 8, 2)
    plan.add_wave(NinjaBee, 4, 12, 2)
    plan.add_wave(Wasp, 4, 16, 2)

    #Boss Stage
    for time in range(21, 30, 2):
        plan.add_wave(Bee, 4, time, 3)
    plan.add_wave(Wasp, 4, 22, 2)
    plan.add_wave(Hornet, 4, 24, 2)
    plan.add_wave(NinjaBee, 4, 26, 2)
    plan.add_wave(Hornet, 4, 28, 2)
    plan.add_wave(Boss, 30, 30, 1)
    return plan

def make_insane_assault_plan():
    plan = AssaultPlan()
    plan.add_wave(Hornet, 5, 2, 2)
    for time in range(3, 16, 2):
        plan.add_wave(Bee, 5, time, 2)
    plan.add_wave(Hornet, 5, 4, 2)
    plan.add_wave(Wasp, 5, 8, 2)
    plan.add_wave(NinjaBee, 5, 12, 2)
    plan.add_wave(Wasp, 5, 16, 2)

    #Boss Stage
    for time in range(21, 30, 2):
        plan.add_wave(Bee, 5, time, 3)
    plan.add_wave(Wasp, 5, 22, 2)
    plan.add_wave(Hornet, 5, 24, 2)
    plan.add_wave(NinjaBee, 5, 26, 2)
    plan.add_wave(Hornet, 5, 28, 2)
    plan.add_wave(Boss, 30, 30, 2)
    return plan


from utils import *
@main
def run(*args):
    Insect.reduce_armor = class_method_wrapper(Insect.reduce_armor,
            pre=print_expired_insects)
    start_with_strategy(args, interactive_strategy)

