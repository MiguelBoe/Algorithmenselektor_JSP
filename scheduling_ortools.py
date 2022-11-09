"""
@author: pretz & böttcher

#-----------------------------------------------------------------------------#
#         Projektseminar Business Analytics - Wintersemester 22/23            #
#-----------------------------------------------------------------------------#
#                      CP Solver - Ortools by google                          #
#                                                                             #
#-----------------------------------------------------------------------------#
"""
import collections
from pyexpat import model
from ortools.sat.python import cp_model

from JobList import JobList


def parameters(jobs_data: list):
    # Anzahl der Maschinen
    num_machines = 1 + max(task[0] for job in jobs_data for task in job)

    # Computes horizon dynamically as the sum of all durations.
    horizon = sum(task[1] for job in jobs_data for task in job)

    return num_machines, horizon


def variables(jobs_data: list, model_JSP):
    # Named tuple to store information about created variables.
    task_type = collections.namedtuple("task_type", "start end interval")

    # Creates job intervals and add to the corresponding machine lists.
    all_tasks = {}
    machine_to_intervals = collections.defaultdict(list)

    for job_id, job in enumerate(jobs_data):
        for task_id, task in enumerate(job):
            machine = task[0]
            duration = task[1]
            suffix = "_%i_%i" % (job_id, task_id)

            # Intvariable
            start_var = model_JSP.NewIntVar(0, horizon, f"start{suffix}")
            end_var = model_JSP.NewIntVar(0, horizon, f"end{suffix}")

            # Intervalvariable
            interval_var = model_JSP.NewIntervalVar(
                start_var, duration, end_var, f"interval{suffix}"
            )

            # dict (tuple(job_id, task_id): tasktype)
            # Speichert alle vorhandenen Tasks
            all_tasks[job_id, task_id] = task_type(
                start=start_var, end=end_var, interval=interval_var
            )

            # defaultdict (machine: list of intervalVAR)
            # Speichert für jede Maschine welche Tasks darauf laufen sollen
            machine_to_intervals[machine].append(interval_var)

    return all_tasks, machine_to_intervals


def constraints(
    jobs_data: list,
    all_tasks: dict[collections.namedtuple],
    num_machines: int,
    machine_to_intervals: collections.defaultdict,
    model,
):

    # keine Maschine darf mehrere Tasks gleichzeitig bearbeiten
    for machine in range(num_machines):
        model.AddNoOverlap(machine_to_intervals[machine])

    # Vorrangsbeziehungen in Jobs
    for job_id, job in enumerate(jobs_data):
        for task_id in range(len(job) - 1):
            model.Add(
                all_tasks[job_id, task_id + 1].start >= all_tasks[job_id, task_id].end
            )

    return model


def obj(horizon):
    # Makespan minimieren.
    obj_var = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(
        obj_var,
        [all_tasks[job_id, len(job) - 1].end for job_id, job in enumerate(jobs_data)],
    )
    model.Minimize(obj_var)

    return model


def solver(model):
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    return solver, status


def solution(status, solver):
    # Named tuple to manipulate solution information.
    assigned_task_type = collections.namedtuple(
        "assigned_task_type", "start job index duration"
    )

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("Solution:")
        # Create one list of assigned tasks per machine.
        assigned_jobs = collections.defaultdict(list)
        for job_id, job in enumerate(jobs_data):
            for task_id, task in enumerate(job):
                machine = task[0]
                assigned_jobs[machine].append(
                    assigned_task_type(
                        start=solver.Value(all_tasks[job_id, task_id].start),
                        job=job_id,
                        index=task_id,
                        duration=task[1],
                    )
                )
        # Create per machine output lines.
        output = ""
        for machine in range(num_machines):
            # Sort by starting time.
            assigned_jobs[machine].sort()
            sol_line_tasks = f"Machine {str(machine)}: "
            sol_line = "           "

            for assigned_task in assigned_jobs[machine]:
                name = "job_%i_task_%i" % (assigned_task.job, assigned_task.index)
                # Add spaces to output to align columns.
                sol_line_tasks += "%-15s" % name

                start = assigned_task.start
                duration = assigned_task.duration
                sol_tmp = "[%i,%i]" % (start, start + duration)
                # Add spaces to output to align columns.
                sol_line += "%-15s" % sol_tmp

            sol_line += "\n"
            sol_line_tasks += "\n"
            output += sol_line_tasks
            output += sol_line

        # Finally print the solution found.
        print(f"Optimal Schedule Length: {solver.ObjectiveValue()}")
        print(output)
    else:
        print("No solution found.")

    # Statistics.
    print("\nStatistics")
    print("  - conflicts: %i" % solver.NumConflicts())
    print("  - branches : %i" % solver.NumBranches())
    print("  - wall time: %f s" % solver.WallTime())
    return


if __name__ == "__main__":

    # Create the model.
    model_JSP = cp_model.CpModel()

    jobs_data = [
        [(0, 5), (1, 3), (2, 3), (3, 2)],
        [(1, 4), (0, 7), (2, 8), (3, 6)],
        [(3, 3), (2, 5), (1, 6), (0, 1)],
        [(2, 4), (3, 7), (1, 1), (0, 2)],
    ]
    # jobs_data = JobList(jobs_data)

    num_machines, horizon = parameters(jobs_data)

    all_tasks, machine_to_intervals = variables(jobs_data, model_JSP)

    model_JSP = constraints(
        jobs_data, all_tasks, num_machines, machine_to_intervals, model_JSP
    )
    solver, status = solver(model_JSP)
    solution(status, solver)