from __future__ import annotations
import dataclasses as _dataclasses
from enum import unique
import json
import timeit, random, itertools
from types import NoneType
from typing import Any, Callable, Generator, Optional, Sequence, overload
from .make_repr import make_repr


def none_filter(item) -> bool:
    return item is not None


class Differentials:
    def __init__(
        self,
        tc     : TeamContainer,
        rgd_dv : int = 0,
        vgd_dv : int = 0,
        rsd_dv : int = 0,
        vsd_dv : int = 0
    ) -> None:
        """Creates a differential container object with the given teams and optional default values."""
        self.repr = make_repr(
            Differentials.__init__,
            (tc,),
            (rgd_dv, "rgd_dv"),
            (vgd_dv, "vgd_dv"),
            (rsd_dv, "rsd_dv"),
            (vsd_dv, "vsd_dv"),
            fail_value = 0
        )

        # populate indexes
        rgd_values  : list[int]            = []
        rgd_indexes : dict[str | int, int] = {}
        for i, team in enumerate(tc._teams):
            rgd_values.append(rgd_dv)
            rgd_indexes[team.name] = i
            rgd_indexes[team.id]   = i
            for alias in team.aliases:
                rgd_indexes[alias] = i
        
        # create DifferentialContainer and copy to rest
        self.rgd : Differentials.DifferentialContainer = Differentials.DifferentialContainer(rgd_values, rgd_indexes)
        self.vgd : Differentials.DifferentialContainer = self.rgd.copy(vgd_dv)
        self.rsd : Differentials.DifferentialContainer = self.rgd.copy(rsd_dv)
        self.vsd : Differentials.DifferentialContainer = self.rgd.copy(vsd_dv)


    def __repr__(self) -> str:
        return self.repr
    

    def add_raw(self, identifier: team_identifier, rgd: int, vgd: int, rsd: int, vsd: int) -> None:
        self.rgd[identifier] += rgd
        self.vgd[identifier] += vgd
        self.rsd[identifier] += rsd
        self.vsd[identifier] += vsd
    

    def combine(self, *dfs: Differentials) -> None:
        """Combines the input differentials with this object's differentials"""
        for df in dfs:
            for inside_diff, outside_diff in [(self.rgd, df.rgd), (self.vgd, df.vgd), (self.rsd, df.rsd), (self.vsd, df.vsd)]:
                # find all unique indexes and their identifiers
                unique_indexes: dict[int, list[int | str]] = {}
                for identifier, index in outside_diff._indexes.items():
                    if outside_diff._values[index] == 0:
                        continue
                    if index not in unique_indexes:
                        unique_indexes[index] = []
                    unique_indexes[index].append(identifier)
                
                # attempt to add outside diffs to inside diffs
                for index, identifiers in unique_indexes.items():
                    for identifier in identifiers:
                        if identifier in inside_diff._indexes:
                            inside_diff[identifier] += outside_diff._values[index]
                            break
    

    class DifferentialContainer:
        def __init__(self, __values: list[int], __indexes: dict[str | int, int]) -> None:
            self.repr = make_repr(
                Differentials.DifferentialContainer.__init__,
                (__values,),
                (__indexes,)
            )
            self._values  = __values
            self._indexes = __indexes
        

        def __repr__(self) -> str:
            return self.repr


        def __str__(self) -> str:
            keys_by_index = [[] for _ in self._values]
            for k, v in self._indexes.items():
                keys_by_index[v].append(k)
            lines = []
            for keys, value in zip(keys_by_index, self._values):
                lines.append(" | ".join([json.dumps(key) for key in keys]) + f" : {value}")
            return "\n".join(lines)


        def _get_team_index(self, __k: team_identifier) -> str:
            if isinstance(__k, Team):
                __k = __k.id
            if __k not in self._indexes:
                raise KeyError(f"team with name, id or alias \"{__k}\" does not exist")
            return self._indexes[__k]
        

        def __getitem__(self, __k: team_identifier) -> int:
            return self._values[self._get_team_index(__k)]
        

        def get(self, identifier: team_identifier) -> int:
            return self._values[self._get_team_index(identifier)]


        def __setitem__(self, __k: team_identifier, __v: int) -> None:
            self._values[self._get_team_index(__k)] = __v
        

        def set(self, identifier: team_identifier, value: int) -> None:
            self._values[self._get_team_index(identifier)] = value
        

        @overload
        def copy(self) -> Differentials.DifferentialContainer: ...
        @overload
        def copy(self, default_value: int) -> Differentials.DifferentialContainer: ...
        def copy(self, default_value: int = None) -> Differentials.DifferentialContainer:
            return Differentials.DifferentialContainer([default_value for _ in self._values] if default_value is not None else self._values, self._indexes)
        

        @overload
        def reset(self) -> None: ...
        @overload
        def reset(self, default_value: int) -> None: ...
        def reset(self, default_value: int = 0) -> None:
            self._values = [default_value for _ in self._values]


class Team:
    """Represents a team."""
    def __init__(self, id: int, name: str, *aliases: str) -> None:
        self.repr = make_repr(
            Team.__init__,
            (id,),
            (name,),
            *[(alias,) for alias in aliases],
            fail_value = ()
        )
        self.id      = id
        self.name    = name
        self.aliases = aliases
    

    def __repr__(self) -> str:
        return self.repr


class TeamContainer:
    def __init__(self) -> None:
        """Represents a group of teams."""
        self._teams   : list[Team]         = []
        self._indexes : dict[str|int, int] = {}


    def __repr__(self) -> str:
        return "TeamContainer()"


    def _get_team_index(self, __k: team_identifier) -> str:
        if isinstance(__k, Team):
            __k = __k.id
        if __k not in self._indexes:
            raise KeyError(f"team with name, id or alias \"{__k}\" does not exist")
        return self._indexes[__k]


    def _check_for_duplicate_team(self, team: Team) -> None:
        if team.name in self._indexes:
            raise ValueError(f"team with name \"{team.name}\" already exists")
        if team.id in self._indexes:
            raise ValueError(f"team with id \"{team.id}\" already exists")
        for alias in team.aliases:
            if alias in self._indexes:
                raise ValueError(f"team with alias \"{alias}\" already exists")


    def _add_team(self, team: Team) -> None:
        index = len(self._teams)
        self._teams.append(team)
        self._indexes[team.name] = index
        self._indexes[team.id] = index
        for alias in team.aliases:
            self._indexes[alias] = index


    def register(self, team: Team) -> None:
        """Registers a new team with a provided Team object."""
        self._check_for_duplicate_team(team)
        self._add_team(team)


    def __getitem__(self, __k: team_identifier) -> Team:
        return self._teams[self._get_team_index(__k)]
    

    def get(self, identifier: team_identifier) -> Team:
        return self._teams[self._get_team_index(identifier)]


class Series:
    def __init__(self, team_1: Team, team_2: Team, rscore_1: int, rscore_2: int, rwin_1: bool = None, rwin_2: bool = None, vscore_1: int  = None, vscore_2: int  = None, vwin_1: bool = None, vwin_2: bool = None) -> None:
        """Represents the results of one series played between two teams"""
        self.repr     = make_repr(
            Series.__init__,
            (team_1,),
            (team_2,),
            (rscore_1,),
            (rscore_2,),
            (rwin_1, "rwin_1"),
            (rwin_2, "rwin_2"),
            (vscore_1, "vscore_1"),
            (vscore_2, "vscore_2"),
            (vwin_1, "vresult_1"),
            (vwin_2, "vresult_2"),
            fail_value = None
        )
        self.team_1   = team_1
        self.team_2   = team_2
        self.rscore_1 = rscore_1
        self.rscore_2 = rscore_2
        self.rwin_1   = rwin_1   or True if rscore_1 > rscore_2 else False
        self.rwin_2   = rwin_2   or True if rscore_1 < rscore_2 else False
        self.vscore_1 = vscore_1 or rscore_1
        self.vscore_2 = vscore_2 or rscore_2
        self.vwin_1   = vwin_1   or self.rwin_1
        self.vwin_2   = vwin_2   or self.rwin_2
        self.exhaused = False
    

    def __repr__(self) -> str:
        return self.repr


class SeriesContainer:
    def __init__(self, tc: TeamContainer) -> None:
        """Contains series results of multiple matchups"""
        self.repr = make_repr(
            SeriesContainer.__init__,
            (tc,)
        )
        self._tc      : TeamContainer              = tc
        self._indexes : dict[tuple[int, int], int] = {}
        self._series  : list[list[Series]]         = []
    

    def __repr__(self) -> str:
        return self.repr


    def register(self, series: Series) -> None:
        """Registers a new series to the SeriesContainer"""
        matchup = (series.team_1.id, series.team_2.id)
        if matchup in self._indexes:
            self._series[self._indexes[matchup]].append(series)
            return
        index = len(self._series)
        self._series.append([series])
        self._indexes[matchup] = index
        self._indexes[tuple(reversed(matchup))] = index


    def _get_series(self, __k1: team_identifier, __k2: team_identifier) -> Series:
        t1 = self._tc.get(__k1)
        t2 = self._tc.get(__k2)
        matchup = (t1.id, t2.id)
        if matchup in self._indexes:
            series = self._series[self._indexes[matchup]]
            for series_ in series:
                if not series_.exhaused:
                    series_.exhaused = True
                    return series_


    def __getitem__(self, __k: tuple[team_identifier, team_identifier]) -> Series:
        return self._get_series(*__k)
    

    def get(self, identifier1: team_identifier, identifier2: team_identifier) -> Series:
        return self._get_series(identifier1, identifier2)
    

    def get_played_series(self) -> list[Series]:
        series_played: list[Series] = []
        for series_list in self._series:
            for series in series_list:
                if series.exhaused:
                    series_played.append(series)
        return series_played


class Seeding:
    def __init__(self, tc: TeamContainer) -> None:
        self._tc          : TeamContainer = tc
        self.seeding_     : list[Team]    = []


    def set(self, *identifiers: team_identifier) -> Seeding:
        """Sets the seeding by insertion order; returns this instance (for chaining)"""
        self.seeding_ = [self._tc[id] if id is not None else None for id in identifiers]
        return self
    

    def __getitem__(self, __k: int) -> Team:
        if len(self.seeding_) > __k:
            return self.seeding_[__k]
    

    def __setitem__(self, __k: int, __v: Team) -> Seeding:
        if len(self.seeding_) > __k:
            self.seeding_[__k] = __v
            return self
        self.seeding_ += [None] * (__k - (len(self.seeding_) - 1))
        self.seeding_[__k] = __v
        return self


    def _get_rematch_permutations(self) -> Generator[tuple[int], None, None]:
        num_teams    : int = len(self.seeding_)
        team_indexes : list[int] = list(range(0, num_teams))
        for permutation in itertools.permutations(team_indexes, num_teams):
            yield permutation


    def sort(self, *sort_by: tuple[int, Differentials.DifferentialContainer | Callable[[], Differentials.DifferentialContainer] | Seeding | Callable[[], Seeding]]) -> Seeding:
        """Sorts in order of insert (tiebreaker); `[0]` is the coefficient, and `[1]` is the DifferentialContainer or Seeding object; returns this instance (for chaining)"""
        _sort_by: list[tuple[int, Differentials.DifferentialContainer | Seeding]] = []
        for coef, criteria in sort_by:
            _sort_by.append((coef, (criteria if isinstance(criteria, (Differentials.DifferentialContainer, Seeding)) else criteria())))
        if not all(team is not None for team in self.seeding_):
            return self
        def sorter(team: Team) -> bool:
            return [criteria[team] * coef if isinstance(criteria, Differentials.DifferentialContainer) else coef * criteria.seeding_.index(team) for coef, criteria in _sort_by]
        self.seeding_.sort(key = sorter)
        return self
    

    @overload
    def sort_no_rematches(self, sc: SeriesContainer, si: Callable[[Seeding], list[tuple[Team, Team]]]) -> Seeding: ...
    @overload
    def sort_no_rematches(self, sc: SeriesContainer, si: Callable[[Seeding], list[tuple[Team, Team]]], *sort_by: tuple[int, Differentials.DifferentialContainer | Seeding]) -> Seeding: ...
    def sort_no_rematches(self, sc: SeriesContainer, si: Callable[[Seeding], list[tuple[Team, Team]]], *sort_by: tuple[int, Differentials.DifferentialContainer | Seeding]) -> Seeding:
        """Runs through all matchup permutations in fair order until a set of matchups is found that has yet to be played (all matchups in the set must not have been played before in order to succeed); if `sort_by` is included, it will first sort the seeding with the given sort parameters, then try to eliminate rematches."""
        # do an initial sort
        if sort_by:
            self.sort(*sort_by)

        # find rematch permutations and series played
        rematch_permutations     : Generator[tuple[int], None, None] = self._get_rematch_permutations()
        series_played            : list[Series]                      = sc.get_played_series()

        # get matchups as indexes of seeding
        previous_matchup_indexes : list[tuple[int]]                  = [(self.seeding_.index(series.team_1), self.seeding_.index(series.team_2)) for series in series_played if series.team_1 in self.seeding_ and series.team_2 in self.seeding_]
        previous_matchup_indexes += [tuple(reversed(matchup)) for matchup in previous_matchup_indexes]
        # loop through permutations
        for rematch_permutation in rematch_permutations:
            # interpret permutation using our SeedingInterpreter
            interpreted   : list[tuple[int, int]] = si(rematch_permutation)
            rematch_found : bool                  = False
            # loop through matchups in the interpreted permutations and make sure each was not played, otherwise break and continue to the next permutation
            for matchup in interpreted:
                if matchup in previous_matchup_indexes:
                    rematch_found = True
                    break
            # set new seeding if all matches are not rematches
            if not rematch_found:
                self.seeding_ = [self.seeding_[index] for index in rematch_permutation]
                return self


    def seeding(self) -> list[Team]:
        """Returns the seeding"""
        return self.seeding_


class SeedingInterpreter:
    @staticmethod
    def standard(sg: Seeding | list[Team]) -> list[tuple[Team, Team]]:
        seeding = [] + (list(sg.seeding_) if isinstance(sg, Seeding) else list(sg))
        if len(seeding) % 2:
            seeding.pop()
        half = len(seeding) // 2
        return list(zip(seeding[:half], seeding[half:]))
    
    
    @staticmethod
    def reversed(sg: Seeding | list[Team]) -> list[tuple[Team, Team]]:
        seeding = [] + (list(sg.seeding_) if isinstance(sg, Seeding) else list(sg))
        if len(seeding) % 2:
            seeding.pop()
        half = len(seeding) // 2
        return list(zip(seeding[:half], list(reversed(seeding[half:]))))
    
    
    @staticmethod
    def random(sg: Seeding | list[Team]) -> list[tuple[Team, Team]]:
        seeding = [] + (list(sg.seeding_) if isinstance(sg, Seeding) else list(sg))
        random.shuffle(seeding)
        if len(seeding) % 2:
            seeding.pop()
        half = len(seeding) // 2
        return list(zip(seeding[:half], seeding[half:]))
        

team_identifier  = Team | str | int
team_fetcher     = Team | Callable[[], Team]
seed_fetcher     = Seeding | Callable[[], Seeding]
seed_interpreter = Callable[[Seeding], list[tuple[Team, Team]]]


class Matchup:
    def __init__(self, team_1: team_fetcher, team_2: team_fetcher) -> None:
        self.repr = make_repr(
            Matchup.__init__,
            (team_1,),
            (team_2,)
        )
        self.team_1 = team_1
        self.team_2 = team_2
        self.result_ = self.Result()
    

    def __repr__(self) -> str:
        return self.repr


    @overload
    def calculate(self, tc: TeamContainer, sc: SeriesContainer) -> Matchup.Result: ...
    @overload
    def calculate(self, tc: TeamContainer, sc: SeriesContainer, df: Differentials) -> Matchup.Result: ...
    def calculate(self, tc: TeamContainer, sc: SeriesContainer, df: Differentials = None) -> Matchup.Result:
        # get series
        team_1 = None if self.team_1 is None else self.team_1 if isinstance(self.team_1, Team) else self.team_1()
        team_2 = None if self.team_2 is None else self.team_2 if isinstance(self.team_2, Team) else self.team_2()
        if team_1 is None or team_2 is None:
            self.result_ = self.Result(team_1, team_2)
            return self.result_
        series = sc[team_1, team_2]
        if not series:
            self.result_ = self.Result(team_1, team_2)
            return self.result_
        
        # create idf
        idf = Differentials(sc._tc)

        # get data from series
        t1_data = (series.rscore_1, series.vscore_1, series.rwin_1, series.vwin_1)
        t2_data = (series.rscore_2, series.vscore_2, series.rwin_2, series.vwin_2)

        # assign data to variables and ensure data team matches self team
        t1_rs, t1_vs, t1_rw, t1_vw, t2_rs, t2_vs, t2_rw, t2_vw = (*t1_data, *t2_data) if series.team_1 == team_1 else (*t2_data, *t1_data)
        
        # apply differentials if df is defined
        t1_diffs = (
            t1_rs - t2_rs,
            t1_vs - t2_vs,
            1 if t1_rw else -1,
            1 if t1_vw else -1
        )
        t2_diffs = (
            t2_rs - t1_rs,
            t2_vs - t1_vs,
            1 if t2_rw else -1,
            1 if t2_vw else -1
        )
        idf.add_raw(team_1, *t1_diffs)
        idf.add_raw(team_2, *t2_diffs)
        if df is not None:
            df.add_raw(team_1, *t1_diffs)
            df.add_raw(team_2, *t2_diffs)
        
        # return full result
        self.result_ = self.Result(
            team_1,
            team_2,
            t1_rs,
            t2_rs,
            t1_vs,
            t2_vs,
            t1_rw,
            t2_rw,
            t1_vw,
            t2_vw,
            t1_rs > t2_rs,
            t1_rs < t2_rs,
            *(team_1, team_2, t1_rs, t2_rs) if t1_rs > t2_rs else (team_2, team_1, t2_rs, t1_rs),
            df,
            idf
        )
        return self.result_


    def result(self) -> Optional[Matchup.Result]:
        return self.result_
    

    def winner(self) -> Optional[Team]:
        if self.result_:
            return self.result_.winner
    

    def loser(self) -> Optional[Team]:
        if self.result_:
            return self.result_.loser
    

    def idf(self) -> Optional[Differentials]:
        if self.result_:
            return self.result_.idf


    class Result:
        @overload
        def __init__(self) -> None: ...
        @overload
        def __init__(self, team_1: Team, team_2: Team) -> None: ...
        @overload
        def __init__(self, team_1: Team, team_2: Team, rscore_1: int, rscore_2: int, vscore_1: int, vscore_2: int, rwin_1: bool, rwin_2: bool, vwin_1: bool, vwin_2: bool, is_winner_1: bool, is_winner_2: bool, winner: Team, loser: Team, winner_rscore: int, loser_rscore: int) -> None: ...
        @overload
        def __init__(self, team_1: Team, team_2: Team, rscore_1: int, rscore_2: int, vscore_1: int, vscore_2: int, rwin_1: bool, rwin_2: bool, vwin_1: bool, vwin_2: bool, is_winner_1: bool, is_winner_2: bool, winner: Team, loser: Team, winner_rscore: int, loser_rscore: int, df: Differentials, idf: Differentials) -> None: ...
        def __init__(self, team_1: Team = None, team_2: Team = None, rscore_1: int = None, rscore_2: int = None, vscore_1: int = None, vscore_2: int = None, rwin_1: bool = None, rwin_2: bool = None, vwin_1: bool = None, vwin_2: bool = None, is_winner_1: bool = None, is_winner_2: bool = None, winner: Team = None, loser: Team = None, winner_rscore: int = None, loser_rscore: int = None, df: Differentials = None, idf: Differentials = None) -> None:
            self.repr = make_repr(
                Matchup.Result.__init__,
                (team_1, "team_1"),
                (team_2, "team_2"),
                (rscore_1, "rscore_1"),
                (rscore_2, "rscore_2"),
                (vscore_1, "vscore_1"),
                (vscore_2, "vscore_2"),
                (rwin_1, "rwin_1"),
                (rwin_2, "rwin_2"),
                (vwin_1, "vwin_1"),
                (vwin_2, "vwin_2"),
                (is_winner_1, "is_winner_1"),
                (is_winner_2, "is_winner_2"),
                (winner, "winner"),
                (loser, "loser"),
                (winner_rscore, "winner_rscore"),
                (loser_rscore, "loser_rscore"),
                (df, "df"),
                (idf, "idf"),
                fail_value = None
            )
            self.team_1        : Team          = team_1
            self.team_2        : Team          = team_2
            self.rscore_1      : int           = rscore_1 
            self.rscore_2      : int           = rscore_2 
            self.vscore_1      : int           = vscore_1 
            self.vscore_2      : int           = vscore_2 
            self.rwin_1        : bool          = rwin_1 
            self.rwin_2        : bool          = rwin_2 
            self.vwin_1        : bool          = vwin_1 
            self.vwin_2        : bool          = vwin_2 
            self.is_winner_1   : bool          = is_winner_1 
            self.is_winner_2   : bool          = is_winner_2 
            self.winner        : Team          = winner 
            self.loser         : Team          = loser 
            self.winner_rscore : int           = winner_rscore 
            self.loser_rscore  : int           = loser_rscore 
            self.df            : Differentials = df
            self.idf           : Differentials = idf


        def __repr__(self) -> str:
            return self.repr


class MatchSet:
    def __init__(self, sg: seed_fetcher, si: seed_interpreter) -> None:
        self._sg     : seed_fetcher     = sg
        self._si     : seed_interpreter = si
        self.result_ : MatchSet.Result  = None

    
    @overload
    def calculate(self, tc: TeamContainer, sc: SeriesContainer) -> MatchSet.Result: ...
    @overload
    def calculate(self, tc: TeamContainer, sc: SeriesContainer, df: Differentials) -> MatchSet.Result: ...
    def calculate(self, tc: TeamContainer, sc: SeriesContainer, df: Differentials = None) -> MatchSet.Result:
        """Calculate the results of the match set"""
        # get matchups from seeding
        seeding         : Seeding                 = self._sg if isinstance(self._sg, Seeding) else self._sg()
        team_matchups   : list[tuple[Team, Team]] = self._si(seeding)
        matchups        : list[Matchup]           = [Matchup(team_1, team_2) for team_1, team_2 in team_matchups]

        # calculate each result
        matchup_results : list[Matchup.Result] = []
        for matchup in matchups:
            result = matchup.calculate(tc, sc, df)
            matchup_results.append(result)

        # create idf
        idf: Differentials = Differentials(tc)
        idf.combine(*list(filter(none_filter, [result.idf for result in matchup_results])))
        
        # get seeding objects from winning and losing teams
        winning_teams   : list[Optional[Team]] = [result.winner for result in matchup_results]
        # print(winning_teams)
        losing_teams    : list[Optional[Team]] = [result.loser for result in matchup_results]
        # print(losing_teams)
        winning_seeding : Seeding = Seeding(tc)
        losing_seeding  : Seeding = Seeding(tc)
        winning_seeding.set(*winning_teams)
        losing_seeding.set(*losing_teams)

        # create and return result
        self.result_ = self.Result(matchup_results, winning_seeding, losing_seeding, idf, df)
        return self.result_
    

    def result(self) -> Optional[MatchSet.Result]:
        return self.result_


    class Result:
        @overload
        def __init__(self, results: list[Matchup.Result], winners: Seeding, losers: Seeding, idf: Differentials) -> None: ...
        @overload
        def __init__(self, results: list[Matchup.Result], winners: Seeding, losers: Seeding, idf: Differentials, df: Differentials) -> None: ...
        def __init__(self, results: list[Matchup.Result], winners: Seeding, losers: Seeding, idf: Differentials, df: Differentials = None) -> None:
            self.repr = make_repr(
                MatchSet.Result.__init__,
                (results,),
                (winners,),
                (losers,),
                (idf,),
                (df, "df"),
                fail_value = None
            )
            self.results : list[Matchup.Result] = results
            self.winners : Seeding              = winners
            self.losers  : Seeding              = losers
            self.idf     : Differentials        = idf
            self.df      : Differentials        = df
        

        def __repr__(self) -> str:
            return self.repr
            

class BracketModel:
    def __init__(self) -> None:
        self.tc        : TeamContainer                               = None
        self.df        : Differentials                               = None
        self.sc        : SeriesContainer                             = None
        self.sg        : Seeding                                     = None
        self._matchups : dict[Any, Matchup | MatchSet]               = {}
        self.results   : dict[Any, Matchup.Result | MatchSet.Result] = {}
        self.complete  : bool                                        = False
    

    def __repr__(self) -> str:
        return "BracketModel()"


    def __getitem__(self, __k: Any) -> Matchup | MatchSet:
        return self._matchups[__k]


    def __setitem__(self, __k: Any, __v: Any) -> None:
        self._matchups[__k] = __v


    def next(self, key: Any, match: Matchup | MatchSet) -> None:
        self._matchups[key] = match
    

    def calculate(self, sg: Seeding, tc: TeamContainer, sc: SeriesContainer, df: Differentials) -> None:
        self.tc : TeamContainer   = tc
        self.df : Differentials   = df
        self.sc : SeriesContainer = sc
        self.sg : Seeding         = sg
        self.complete = True
        for k, v in self._matchups.items():
            self.results[k] = v.calculate(self.tc, self.sc, self.df)
            if (self.results[k].winner if isinstance(self.results[k], Matchup.Result) else self.results[k].winners[0]) is None:
                self.complete = False
