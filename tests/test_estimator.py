import pytest

import numpy as np

from taser.trajectory_estimator import TrajectoryEstimator
from taser._ceres import CallbackReturnType

@pytest.fixture
def estimator(trajectory):
    return TrajectoryEstimator(trajectory)

def test_same_trajectory(trajectory):
    "Test that we can create estimators for all trajectory types"
    estimator = TrajectoryEstimator(trajectory)
    assert estimator.trajectory is trajectory


def test_solve_empty(estimator):
    summary = estimator.solve()
    print(summary.FullReport())
    assert summary.num_parameters == 0


def _test_add_measurement(estimator, measurements):
    for m in measurements:
        estimator.add_measurement(m)


def test_add_camera_measurement(estimator, camera_measurements):
    _test_add_measurement(estimator, camera_measurements)


def test_add_simple_measurements(estimator, simple_measurements):
    _test_add_measurement(estimator, simple_measurements)


def test_add_imu_measurements(estimator, imu_measurements):
    _test_add_measurement(estimator, imu_measurements)


def test_solve_simple_nocrash(estimator, simple_measurements):
    _test_add_measurement(estimator, simple_measurements)
    summary = estimator.solve()
    print(summary.FullReport())
    assert summary.num_parameters > 0


def test_solve_camera_nocrash(estimator, camera_measurements):
    _test_add_measurement(estimator, camera_measurements)
    summary = estimator.solve()
    print(summary.FullReport())
    assert summary.num_parameters > 0


def test_trajectory_lock(trajectory, simple_measurements):
    estimator_unlocked = TrajectoryEstimator(trajectory)
    for m in simple_measurements:
        estimator_unlocked.add_measurement(m)

    summary_unlocked = estimator_unlocked.solve()
    assert summary_unlocked.num_parameters > 0, "Measurements generated no parameters"
    print('U', summary_unlocked.num_parameters_reduced)

    estimator_locked = TrajectoryEstimator(trajectory)
    trajectory.locked = True
    for m in simple_measurements:
        estimator_locked.add_measurement(m)

    summary_locked = estimator_locked.solve()
    print('L', summary_locked.num_parameters_reduced)

    print(summary_unlocked.FullReport())
    print(summary_locked.FullReport())

    assert summary_locked.num_parameters_reduced == 0, "Not locked"


@pytest.fixture
def callback_estimator():
    from taser.trajectories import SplitTrajectory
    from taser.measurements import PositionMeasurement
    from conftest import trajectory as gen_trajectory

    class Dummy:
        param = SplitTrajectory

    trajectory = gen_trajectory(Dummy)

    estimator = TrajectoryEstimator(trajectory)

    for t in np.linspace(*trajectory.valid_time, endpoint=False, num=20):
        m = PositionMeasurement(t, np.random.uniform(-2, 3, size=3))
        estimator.add_measurement(m)

    return estimator


def test_estimator_callback_returntype_none(callback_estimator):
    data = []
    def my_callback(iter_summary):
        data.append('Foo')

    callback_estimator.add_callback(my_callback)

    summary = callback_estimator.solve(max_iterations=4)
    print(summary.FullReport())

    assert len(data) > 1


def test_estimator_callback_abort(callback_estimator):
    data = []
    def abort_on_two(iter_summary):
        data.append('Foo')
        if iter_summary.iteration == 2:
            return CallbackReturnType.Abort

    callback_estimator.add_callback(abort_on_two)

    summary = callback_estimator.solve(max_iterations=4)

    assert len(data) == 3  # First iteration is 0


def test_estimator_callback_multiple(callback_estimator):
    from collections import Counter
    class Foo:
        returned = []

        def __init__(self, x):
            self.x = x

        def callback(self, iter_summary):
            Foo.returned.append(self.x)

    foos = [Foo(i) for i in range(10)]

    for foo in foos:
        callback_estimator.add_callback(foo.callback)

    summary = callback_estimator.solve(max_iterations=5)

    counter = Counter(Foo.returned)

    # They should have been called an equal amount of times
    for i in range(1, 10):
        assert counter[i] > 1 and counter[i] == counter[0]
