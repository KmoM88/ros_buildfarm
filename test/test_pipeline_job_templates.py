# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from collections import namedtuple
from xml.etree import ElementTree

from ros_buildfarm.templates import expand_template

Repository = namedtuple('Repository', 'url version')


def _base_job_data(**overrides):
    data = {
        'github_url': 'https://github.com/ros2/rcutils/',
        'job_priority': 20,
        'node_label': 'buildagent',
        'disabled': False,
        'ros_buildfarm_repository': Repository(
            'git://repo/ros_buildfarm.git', 'rossif/lyrical-pipelines-iter1'),
        'repository_urls': ['http://repo/ubuntu/building', 'http://repo.ros2.org/ubuntu/building'],
        'repository_keys': ['-----BEGIN PGP PUBLIC KEY BLOCK-----\nLOCAL\n-----END PGP PUBLIC KEY BLOCK-----', 'OSRFKEY'],
        'target_repository': 'http://repo/ubuntu/building',
        'rosdistro_index_url': 'http://repo/rosdistro/index-v4.yaml',
        'rosdistro_name': 'lyrical',
        'release_build_name': 'default',
        'pkg_name': 'rcutils',
        'debian_package_name': 'ros-lyrical-rcutils',
        'os_name': 'ubuntu',
        'os_code_name': 'resolute',
        'arch': 'amd64',
        'import_package_job_name': 'Lrel_import-package',
        'credential_id': 'jenkins-agent',
        'upload_host': 'repo',
        'git_ssh_credential_id': None,
        'timeout_minutes': 90,
        'pipeline_shared_library': 'ros-buildfarm-pipelines@main',
        'docker_mode': 'shared-generator-and-base',
        'docker_base_image_override': 'registry:5000/ros-buildfarm/binarydeb-base-lyrical-amd64',
        'prebaked_base_image': True,
        'orchestration_mode': 'reverse-trigger',
        'upstream_projects': [
            'Lsrc_uR__rcutils__ubuntu_resolute__source',
            'Lbin_uR64__ament_cmake__ubuntu_resolute_amd64__binary',
        ],
        'child_projects': ['Lrel_sync-packages-to-testing_resolute_amd64'],
        'shared_ccache': True,
        'build_environment_variables': ['MAKEFLAGS=-j2'],
        'skip_tests': True,
        'skip_rosdep_keys': ['ignored_dep'],
        'append_timestamp': True,
    }
    data.update(overrides)
    return data


def test_sourcepkg_pipeline_job_template_xml():
    xml_str = expand_template('release/deb/sourcepkg_pipeline_job.xml.em', _base_job_data())
    assert xml_str.startswith('<flow-definition plugin="workflow-job">')
    root = ElementTree.fromstring(xml_str)
    assert root.tag == 'flow-definition'
    assert root.find('.//numToKeep').text == '10'
    assert root.find('.//artifactNumToKeep').text == '2'
    assert root.find('.//hint').text == 'SURVIVABLE_NONATOMIC'
    assert root.find('.//org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty') is not None
    assert root.find('.//hudson.model.BooleanParameterDefinition/name').text == 'skip_cleanup'
    script = root.find('./definition/script').text
    assert "@Library('ros-buildfarm-pipelines@main') _" in script
    assert 'rosReleaseSourceDeb([' in script
    assert "debianPkgName: 'ros-lyrical-rcutils'" in script
    assert '\\nLOCAL\\n' in script


def test_binarypkg_pipeline_trigger_mutual_exclusion():
    rev_xml = expand_template(
        'release/deb/binarypkg_pipeline_job.xml.em',
        _base_job_data(orchestration_mode='reverse-trigger'))
    rev_root = ElementTree.fromstring(rev_xml)
    trig = rev_root.find('.//jenkins.triggers.ReverseBuildTrigger/upstreamProjects')
    assert trig is not None
    assert 'Lbin_uR64__ament_cmake__ubuntu_resolute_amd64__binary' in trig.text
    rev_script = rev_root.find('./definition/script').text
    assert "orchestrationMode: 'reverse-trigger'" in rev_script
    assert 'triggerSyncOnComplete: true' in rev_script
    assert 'prebakedBaseImage: true' in rev_script

    wave_xml = expand_template(
        'release/deb/binarypkg_pipeline_job.xml.em',
        _base_job_data(orchestration_mode='wave-orchestrator'))
    wave_root = ElementTree.fromstring(wave_xml)
    assert wave_root.find('.//jenkins.triggers.ReverseBuildTrigger') is None
    assert wave_root.find('.//org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty') is None
    wave_script = wave_root.find('./definition/script').text
    assert "orchestrationMode: 'wave-orchestrator'" in wave_script
    assert 'triggerSyncOnComplete: false' in wave_script


def test_pipeline_utility_job_template_xml():
    util_xml = expand_template('release/pipeline_utility_job.xml.em', {
        'job_priority': 35,
        'pipeline_shared_library': 'ros-buildfarm-pipelines@main',
        'entrypoint_name': 'rosReleaseWaveOrchestrator',
        'entrypoint_config': {
            'sourceJobs': ['Lsrc_uR__ament_package__ubuntu_resolute__source'],
            'binaryWaves': [['Lbin_uR64__ament_package__ubuntu_resolute_amd64__binary']],
            'syncJobName': 'Lrel_sync-packages-to-testing_resolute_amd64',
        },
    })
    root = ElementTree.fromstring(util_xml)
    assert root.tag == 'flow-definition'
    assert root.find('.//hint').text == 'SURVIVABLE_NONATOMIC'
    assert root.find('.//numToKeep').text == '10'
    script = root.find('./definition/script').text
    assert 'rosReleaseWaveOrchestrator([' in script
    assert "syncJobName: 'Lrel_sync-packages-to-testing_resolute_amd64'" in script
