# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from types import SimpleNamespace

import pytest
import ros_buildfarm
from ros_buildfarm import git
from ros_buildfarm.config.release_build_file import ReleaseBuildFile
from ros_buildfarm.jenkins import _cached_jobs, configure_job
from ros_buildfarm.scripts.release import run_binarydeb_job
from ros_buildfarm.templates import expand_template


def _release_data(**overrides):
    base = {
        'type': 'release-build', 'version': 2,
        'targets': {'ubuntu': {'resolute': {'amd64': None}}},
        'target_repository': 'http://repo/ubuntu/building',
        'upload_credential_id': 'jenkins-agent',
    }
    return dict(base, **overrides)


def test_version_and_git_repository_overrides(monkeypatch):
    assert ros_buildfarm.__version__ == '4.1.1+rossif.lyrical.pipelines.iter1'
    assert git.FALLBACK_REPOSITORY_URL == 'https://github.com/KmoM88/ros_buildfarm.git'
    assert git.FALLBACK_REPOSITORY_VERSION == 'rossif/lyrical-pipelines-iter1'
    monkeypatch.setenv('ROS_BUILDFARM_REPOSITORY_URL', 'git://repo/ros_buildfarm.git')
    monkeypatch.setenv('ROS_BUILDFARM_REPOSITORY_VERSION', 'custom/branch')
    assert git.get_repository() == ('git://repo/ros_buildfarm.git', 'custom/branch')
    monkeypatch.delenv('ROS_BUILDFARM_REPOSITORY_URL')
    monkeypatch.delenv('ROS_BUILDFARM_REPOSITORY_VERSION')
    monkeypatch.setattr(git, '_get_git_repository_remote_origin', lambda _p: None)
    monkeypatch.setattr(git, '_get_git_repository_version', lambda _p: None)
    assert git.get_repository() == (git.FALLBACK_REPOSITORY_URL, git.FALLBACK_REPOSITORY_VERSION)


def test_release_build_file_schema_and_validation():
    bf = ReleaseBuildFile('default', _release_data())
    assert (bf.pipeline_jobs, bf.prebaked_base_image) == (False, False)
    assert bf.pipeline_shared_library == 'ros-buildfarm-pipelines@main'
    assert (bf.orchestration_mode, bf.docker_mode) == ('reverse-trigger', 'baseline')
    assert (bf.docker_base_image_override, bf.slice_packages) == (None, None)

    custom = ReleaseBuildFile('default', _release_data(
        pipeline_jobs=True, orchestration_mode='wave-orchestrator',
        docker_mode='shared-generator-and-base', prebaked_base_image=True,
        docker_base_image_override='registry:5000/ros-buildfarm/binarydeb-base-lyrical-amd64',
        ros_buildfarm_repository_url='git://repo/ros_buildfarm.git',
        ros_buildfarm_repository_version='rossif/lyrical-pipelines-iter1',
        slice_packages=['ament_package', 'rcutils'],
    ))
    assert custom.pipeline_jobs is True and custom.prebaked_base_image is True
    assert custom.filter_packages(['ament_package', 'other']) == {'ament_package', 'other'}

    for bad in (
        {'pipeline_jobs': 'yes'}, {'orchestration_mode': 'invalid'}, {'docker_mode': 'invalid'},
        {'docker_base_image_override': 'ubuntu:resolute'},
        {'docker_base_image_override': 'registry:5000/ros-buildfarm/base:resolute'},
        {'slice_packages': []},
    ):
        with pytest.raises(ValueError):
            ReleaseBuildFile('default', _release_data(**bad))


def test_configure_job_root_recreate_and_prebaked_dockerfile(tmp_path):
    jobs = {'job1': SimpleNamespace(get_config=lambda: '<project><description>old</description></project>')}
    events = []
    jk = SimpleNamespace(
        jobs=jobs, has_job=jobs.__contains__, get_job=jobs.__getitem__,
        delete_job=lambda n: (events.append(('delete', n)), jobs.pop(n)),
        create_job=lambda n, xml: (events.append(('create', n)), jobs.setdefault(n, SimpleNamespace(get_config=lambda: xml)))[1],
    )
    _cached_jobs.clear()
    flow_xml = '<flow-definition plugin="workflow-job"><description/></flow-definition>'
    configure_job(jk, 'job1', flow_xml, dry_run=True)
    assert events == []
    configure_job(jk, 'job1', flow_xml)
    configure_job(jk, 'job1', '<project><description/></project>')
    assert events == [('delete', 'job1'), ('create', 'job1'), ('delete', 'job1'), ('create', 'job1')]

    task_args = {
        'template_name': 'binarypkg_task', 'os_name': 'ubuntu', 'os_code_name': 'resolute',
        'arch': 'amd64', 'docker_base_image_override': 'registry:5000/ros-buildfarm/base',
        'timezone': 'UTC', 'uid': 1001, 'distribution_repository_keys': [],
        'distribution_repository_urls': [], 'wrapper_scripts': {}, 'install_lists': [],
        'build_environment_variables': [], 'dependencies': ['cmake'],
        'dependency_versions': {'cmake': '3.28'}, 'rosdistro_name': 'lyrical',
        'package_name': 'rcutils', 'binarypkg_dir': '/tmp/binarydeb', 'skip_tests': False,
    }
    raw_df = expand_template('release/deb/binarypkg_task.Dockerfile.em', task_args)
    baked_df = expand_template('release/deb/binarypkg_task.Dockerfile.em', dict(task_args, prebaked_base_image=True))
    assert 'useradd' in raw_df and 'useradd' not in baked_df and 'USER buildfarm' in baked_df

    run_binarydeb_job.main([
        '--rosdistro-index-url', 'http://repo/index.yaml', 'lyrical', 'rcutils', 'ubuntu',
        'resolute', 'amd64', '--binarypkg-dir', '/tmp/bin', '--dockerfile-dir', str(tmp_path),
        '--prebaked-base-image',
    ])
    assert '--prebaked-base-image' in (tmp_path / 'Dockerfile').read_text(encoding='utf-8')
