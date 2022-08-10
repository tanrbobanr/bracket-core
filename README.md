# bracket-core
A flexible tournament bracket system for Python.

# How it works
## Registering Teams
To start, let's quickly go over how results are inputted into any bracket model. First, we will register some teams.
```py
from bracketcore import TeamContainer, Team

tc = TeamContainer()
tc.register(Team(1, "Team A")) # id and name are required
tc.register(Team(2, "Team B", "Team b", "team b")) # optionally, more team aliases can be provided
tc.register(Team(3, "Team C"))
tc.register(Team(4, "Team D"))
```
We can access the teams either by subscripting or by using the `get` method.
```py
tc = ...

print(tc[3])
>>> Team.__init__(3, "Team C")

print(tc.get("Team A"))
>>> Team.__init__(1, "Team A")

print(tc.get("team b")) # aliases can also be used to retrieve a team
>>> Team.__init__(2, "Team B", "Team b", "team b")
```
## Registering Series Results
We now need to register some series results.
```py
from bracketcore import SeriesContainer, Series

tc = ...
sc = SeriesContainer(tc)
sc.register(Series(tc["Team A"], tc["Team B"], 1, 3))
sc.register(Series(tc["Team C"], tc["Team D"], 3, 2))
sc.register(Series(tc["Team B"], tc["Team C"], 0, 3))
```
We can acquire a series played by two given teams either by subscripting or by using the `get` method. Once a series is acquired, it will be marked as `exhausted`, meaning it will no longer be retrievable through the `get` method or by subscripting. Additionally, when acquiring a series, any team identifier may be used (the `Team` object itself, the team's ID, name, any alias, or a callable that returns any of these).
```py
tc = ...
sc = ...

print(sc.get(3, 4))
>>> Series.__init__(Team.__init__(3, "Team C"), Team.__init__(4, "Team D"), 3, 2)

print(sc[3, 4]) # will return None because there are no more non-exhausted instances of that matchup remaining
>>> None
```
## Differentials and Seeding
Finally, before we get to actually creating a bracket model, let's quickly go over a few important classes to keep note of. Namely, `Differentials` and `Seeding`.
```py
tc = ...
sc = ...

from bracketcore import Differentials, Seeding, SeedingInterpreter

df = Differentials(tc)
df.rgd.set("Team B", 3) # sets the team's real game differential in the DifferentialContainer
df.rgd["Team C"] += -2 # subtracts 2 from the team's real game differential in the DifferentialContainer
print(df.rgd)
>>> "Team A" | 1                       : 0
    "Team B" | 2 | "Team b" | "team b" : 3
    "Team C" | 3                       : -2
    "Team D" | 4                       : 0


sg = Seeding(tc)
sg.set(1, 2, 3, 4) # sg.seeding_ and sg.seeding() return a list of Team objects in insertion order
print(sg[0]) # gets the first seed, determined by insertion order
>>> Team.__init__(1, "Team A")

sg.sort((-1, df.rgd), (1, Seeding(tc).set(4, 3, 2, 1))) # sorts by each team's real game differential (descending), then by each team's position in the given seeding object (ascending)
print(sg.seeding())
>>> [Team.__init__(2, "Team B", "Team b", "team b"), Team.__init__(4, "Team D"), Team.__init__(1, "Team A"), Team.__init__(3, "Team C")]

sg.sort_no_rematches(sc, SeedingInterpreter.reversed) # iterates through all matchup permutations of the current seeding and solidifies only when a seeding is found that has no rematches. Worse seeds' matchups are favored to modified before the better seeds
```
## Bracket Models (Simple)
Now that we have our team's and series' registered, and a basic seeding created, let's create a bracket model. In this case, we will make a simple 4-team single-elimination bracket as shown below:

![img](https://cdn.discordapp.com/attachments/1006995452870271058/1006995476198994040/bracket.PNG)

```py
from bracketcore import BracketModel, Matchup

tc = ...
sc = ...
df = ...
sg = ...

def single_elim_4_team() -> BracketModel:
    BR = BracketModel()
    # Series 1
    BR.next("series_1", Matchup(lambda: BR.sg[0], lambda: BR.sg[1])) # gets the first and second seeded teams from the Seeding, which will be determined when the bracket gets calculated. We use callables because the seeding has not yet been determined
    # Series 2
    BR.next("series_2", Matchup(lambda: BR.sg[2], lambda: BR.sg[3]))
    # Series 3
    BR.next("series_3", Matchup(BR["series_1"].winner, BR["series_2"].winner)) # gets the winner from Series 1 and Series 2. These two teams should be accessed from callables, so they aren't hardcoded
    return BR

model = single_elim_4_team() # creates an instance of the model
model.calculate(sg, tc, sc, df) # calculates the model using our initial Seeding, TeamContainer, SeriesContainer, and Differentials
model.results["series_3"] # returns an instance of Matchup.Result (as shown below)

Matchup.Result.__init__(
    team_1        = Team.__init__(2, "Team B", "Team b", "team b"), 
    team_2        = Team.__init__(3, "Team C"),
    rscore_1      = 0,
    rscore_2      = 3,
    vscore_1      = 0, 
    vscore_2      = 3,
    rwin_1        = False,
    rwin_2        = True,
    vwin_1        = False,
    vwin_2        = True,
    is_winner_1   = False,
    is_winner_2   = True,
    winner        = Team.__init__(3, "Team C"),
    loser         = Team.__init__(2, "Team B", "Team b", "team b"),
    winner_rscore = 3,
    loser_rscore  = 0,
    df            = Differentials.__init__(TeamContainer()),
    idf           = Differentials.__init__(TeamContainer()) # instance differentials that only contain the differentials from this specific matchup
)

print(model.complete)
>>> True
```
## Bracket Models (Advanced)
Making a bracket model with simple matchups is definitely useful in many cases (such as elimination-style brackets), but attempting to create a more grouped bracket (such as Swiss) would be quite difficult. Instead, we can use a `MatchSet`, which is essentially a group of matchups. Each `MatchSet` requires a `SeedingInterpreter` - a function that determines how matchups are to be created (e.g. the `standard` interpreter will match seeds up `1v3, 2v4`, whereas the `reversed` interpreter will match them up `1v4, 2v3`). The result of a MatchSet contains `winners` and `losers` (among others), which are `Seeding` instances. Below is a quick example of how one might create a model for the first two rounds of a Swiss bracket.
```py
from bracketcore import MatchSet

def swiss_2_rounds() -> BracketModel:
    BR = BracketModel()
    sorts = [
        (-1, lambda: BR.df.rgd), # first sorting by game differential (descending)
        (1, lambda: BR.sg) # then sorting by the initial seeding (ascending)
    ]
    BR.next("round_1", MatchSet(lambda: BR.sg, SeedingInterpreter.reversed))
    BR.next("round_2_high", MatchSet(
        lambda: BR["round_1"].result_.winners.sort(*sorts),
        SeedingInterpreter.reversed
    ))
    BR.next("round_2_low", MatchSet(
        lambda: BR["round_1"].result_.losers.sort(*sorts),
        SeedingInterpreter.reversed
    ))
    return BR

model = swiss_2_rounds()
model.calculate(sg, tc, sc, df)
```