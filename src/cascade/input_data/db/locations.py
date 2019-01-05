import networkx as nx

from cascade.core.db import db_queries
from cascade.core.log import getLoggers

CODELOG, MATHLOG = getLoggers(__name__)


def location_hierarchy(execution_context):
    """
    The GBD location hierarchy as a networkx graph where each node is the
    location id, and its properties are all properties returned by
    the dbtrees library. For instance

    >>> locations = location_hierarchy(ec)
    >>> assert locations.nodes[1]["level"] == 0
    >>> assert locations.nodes[13]["location_name"] == "Malaysia"
    >>> assert locations.successors(5) == [6, 7, 8]
    >>> assert locations.predecessors(491) == [6]

    Args:
        execution_context: Uses the ``gbd_round_id``.

    Returns:
        nx.DiGraph: Each node is the location id as an integer.
    """
    location_df = db_queries.get_location_metadata(
        location_set_id=35, gbd_round_id=execution_context.parameters.gbd_round_id)
    G = nx.DiGraph()
    G.add_nodes_from([(int(row.location_id), row._asdict()) for row in location_df.itertuples()])
    # GBD encodes the global node as having itself as a parent.
    G.add_edges_from([(int(row.parent_id), int(row.location_id))
                      for row in location_df[location_df.location_id != 1].itertuples()])
    G.graph["root"] = 1  # Global is the root location_id
    return G


def get_descendents(execution_context, children_only=False, include_parent=False):
    """
    Retrieves a parent and direct children, or all descendants, or not the
    parent.

    Args:
        execution_context:
        children_only (bool): Exclude children of the children and below.
        include_parent (bool): Add the parent location to return results.

    Returns:
        set of location IDs
    """
    location_id = execution_context.parameters.location_id
    locations = location_hierarchy(execution_context)
    if children_only:
        nodes = set(locations.successors(location_id))
    else:
        nodes = nx.descendants(locations, location_id)

    if include_parent:
        nodes.add(location_id)
    elif location_id in nodes:
        nodes.remove(location_id)
    # don't include parent and parent isn't in there, so OK.

    return list(nodes)


def location_id_from_location_and_level(execution_context, location_id, target_level):
    """ Find the set of locations from the destination location to
    the ``target_level`` above that location.

    Args:
        execution_context:
        location_id (int): the location to search up from
        target_level (str,int): A level in the hierarchy where 1==global and larger numbers are more detailed
                      and the string "most_detailed" indicates the most detailed level.
                      Must be 1 or greater.

    Returns:
        List[int]: The list of locations from the drill start to the given
                   location.

    Raises:
        ValueError if location_id is itself above target_level in the hierarchy

    NOTE:
        This makes some assumptions about what level will be selectable in epiviz which could change
        in the future. There may be a more future-proof version of this that loads stuff out of the
        epi.cascade_level table instead of hard coding it.
    """
    locations = location_hierarchy(execution_context)
    if target_level == "most_detailed":
        if not list(locations.successors(location_id)):
            return [location_id]
        else:
            raise ValueError(f"Most detailed level selected but location {location_id} has child locations "
                             f"{list(locations.successors(location_id))}")

    else:
        drill_nodes = nx.ancestors(locations, location_id) | {location_id}
        drill = list(nx.topological_sort(nx.subgraph(locations, nbunch=drill_nodes)))
        target_level = int(target_level)
        if target_level <= 0:
            raise ValueError(
                f"Expected a location level greater than 0 but found {target_level}")

        # The -1 here is because epiviz uses a system where global == 1 and
        # central comp uses a system where global == 0
        normalized_target = target_level - 1
        if normalized_target < len(drill):
            return drill[normalized_target:]
        else:
            level_name = {1: "Global", 2: "Super Region", 3: "Region", 4: "Country",
                          5: "Subnational 1"}.get(target_level, str(target_level))
            raise ValueError(
                f"Level '{level_name}' selected but current location is higher in the hierarchy than that")
