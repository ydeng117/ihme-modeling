import os
import sys
import argparse
from copy import deepcopy

from aggregator.aggregators import AggMemEff
from aggregator.operators import WtdSum
from gbd.constants import measures
from hierarchies import dbtrees
from ihme_dimensions import gbdize
from jobmon.client.api import ExecutorParameters

from como.legacy.version import ComoVersion
from como.legacy.common import name_task, get_population
from como.legacy.io import SourceSinkFactory
from como.legacy.tasks.incidence_task import IncidenceTaskFactory
from como.legacy.tasks.simulation_input_task import SimulationInputTaskFactory
from como.legacy.tasks.simulation_task import SimulationTaskFactory


THIS_FILE = os.path.realpath(__file__)


class LocationAggTaskFactory:
    def __init__(self, como_version, task_registry, tool):
        self.como_version = como_version
        self.task_registry = task_registry
        self.agg_loc_set_map = {}
        command_template = (
            "{python} {script} "
            "--como_dir {como_dir} "
            "--component {component} "
            "--sex_id {sex_id} "
            "--year_id {year_id} "
            "--measure_id {measure_id} "
            "--location_set_version_id {location_set_version_id}"
        )
        self.task_template = tool.get_task_template(
            template_name="como_agg",
            command_template=command_template,
            node_args=[
                "component",
                "year_id",
                "sex_id",
                "measure_id",
                "location_set_version_id",
            ],
            task_args=["como_dir"],
            op_args=["python", "script"],
        )

    @staticmethod
    def get_task_name(component, year_id, sex_id, measure_id, location_set_version_id):
        return name_task(
            "como_agg",
            {
                "component": component,
                "year_id": year_id,
                "sex_id": sex_id,
                "measure_id": measure_id,
                "location_set_version_id": location_set_version_id,
            },
        )

    def get_task(self, component, year_id, sex_id, measure_id, location_set_version_id):
        loc_trees = dbtrees.loctree(
            location_set_version_id=location_set_version_id,
            gbd_round_id=self.como_version.gbd_round_id,
            return_many=True,
        )
        agg_locs = []
        for loc_tree in loc_trees:
            agg_locs.extend(
                [
                    node
                    for node in loc_tree.node_ids
                    if node not in [x.id for x in loc_tree.leaves()]
                ]
            )
        for location_id in agg_locs:
            self.agg_loc_set_map[location_id] = location_set_version_id

        upstream_tasks = []
        for location_id in [node.id for node in loc_tree.leaves()]:
            if measure_id == measures.INCIDENCE:
                upstream_name = IncidenceTaskFactory.get_task_name(location_id, sex_id)
            elif measure_id == measures.PREVALENCE and component in [
                "sequela",
                "injuries",
                "impairment",
            ]:
                upstream_name = SimulationInputTaskFactory.get_task_name(location_id, sex_id)
            else:
                upstream_name = SimulationTaskFactory.get_task_name(
                    location_id, sex_id, year_id
                )
            upstream_tasks.append(self.task_registry[upstream_name])

        name = self.get_task_name(
            component, year_id, sex_id, measure_id, location_set_version_id
        )
        exec_params = ExecutorParameters(
            executor_class="SGEExecutor",
            num_cores=25,
            m_mem_free="45G",
            max_runtime_seconds=(60 * 60 * 10),
            queue="all.q",
        )
        task = self.task_template.create_task(
            python=sys.executable,
            script=THIS_FILE,
            como_dir=self.como_version.como_dir,
            component=component,
            year_id=year_id,
            sex_id=sex_id,
            measure_id=measure_id,
            location_set_version_id=location_set_version_id,
            name=name,
            max_attempts=3,
            executor_parameters=exec_params,
            upstream_tasks=upstream_tasks,
        )
        self.task_registry[name] = task
        return task


def _fill_0s(df, draw_source, dimensions):
    filters = draw_source.content_kwargs["filters"].copy()
    dimensions = deepcopy(dimensions)
    dimensions.index_dim.replace_level("location_id", filters["location_id"])
    gbdizer = gbdize.GBDizeDataFrame(dimensions)
    df = gbdizer.fill_empty_indices(df, 0)
    return df


class LocationAggTask:

    n_processes = {"cause": 15, "impairment": 10, "sequela": 10, "injuries": 7}
    chunksize = {"cause": 4, "impairment": 3, "sequela": 3, "injuries": 2}

    def __init__(self, como_version, measure_id, year_id, sex_id):
        self.como_version = como_version
        self.measure_id = measure_id
        self.dimensions = self.como_version.nonfatal_dimensions
        if year_id:
            self.dimensions.simulation_index["year_id"] = year_id
        if sex_id:
            self.dimensions.simulation_index["sex_id"] = sex_id

        self._ss_factory = SourceSinkFactory(como_version)

    def get_source(self, component):
        if component == "cause":
            source = self._ss_factory.cause_result_source
        if component == "impairment":
            source = self._ss_factory.impairment_result_source
        if component == "sequela":
            source = self._ss_factory.sequela_result_source
        if component == "injuries":
            source = self._ss_factory.injuries_result_source
        dim = self.dimensions.get_dimension_by_component(component, self.measure_id)
        source.add_transform(_fill_0s, source, dim)
        return source

    def get_sink(self, component):
        if component == "cause":
            sink = self._ss_factory.cause_result_sink
        if component == "impairment":
            sink = self._ss_factory.impairment_result_sink
        if component == "sequela":
            sink = self._ss_factory.sequela_result_sink
        if component == "injuries":
            sink = self._ss_factory.injuries_result_sink
        return sink

    def run_task(self, location_set_version_id, component):
        source = self.get_source(component)
        sink = self.get_sink(component)
        dimensions = self.dimensions.get_dimension_by_component(component, self.measure_id)

        loc_trees = dbtrees.loctree(
            location_set_version_id=location_set_version_id,
            gbd_round_id=self.como_version.gbd_round_id,
            return_many=True,
        )
        for loc_tree in loc_trees:

            pop = get_population(
                self.como_version,
                age_group_id=dimensions.index_dim.get_level("age_group_id"),
                location_id=[node.id for node in loc_tree.nodes],
                year_id=dimensions.index_dim.get_level("year_id"),
                sex_id=dimensions.index_dim.get_level("sex_id"),
            )
            pop = pop[["age_group_id", "location_id", "year_id", "sex_id", "population"]]

            operator = WtdSum(
                index_cols=[col for col in dimensions.index_names if col != "location_id"],
                value_cols=dimensions.data_list(),
                weight_df=pop,
                weight_name="population",
                merge_cols=["location_id", "year_id", "age_group_id", "sex_id"],
            )

            aggregator = AggMemEff(
                draw_source=source,
                draw_sink=sink,
                index_cols=[col for col in dimensions.index_names if col != "location_id"],
                aggregate_col="location_id",
                operator=operator,
                chunksize=self.chunksize[component],
            )

            aggregator.run(
                loc_tree,
                draw_filters={
                    "measure_id": [self.measure_id],
                    "year_id": dimensions.index_dim.get_level("year_id"),
                    "sex_id": dimensions.index_dim.get_level("sex_id"),
                },
                n_processes=self.chunksize[component],
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute nonfatal aggregate for a year-sex-measure"
    )
    parser.add_argument("--como_dir", type=str, help="directory of como run")
    parser.add_argument("--component", type=str, help="which component to aggregate")
    parser.add_argument("--year_id", type=int, help="year_id to aggregate")
    parser.add_argument("--sex_id", type=int, help="sex_id to aggregate")
    parser.add_argument("--measure_id", type=int, help="measure_id to aggregate")
    parser.add_argument(
        "--location_set_version_id",
        type=int,
        help="location_set_version_id to aggregate",
    )
    args = parser.parse_args()

    cv = ComoVersion(args.como_dir)
    cv.load_cache()
    task = LocationAggTask(cv, args.measure_id, args.year_id, args.sex_id)
    task.run_task(args.location_set_version_id, args.component)
