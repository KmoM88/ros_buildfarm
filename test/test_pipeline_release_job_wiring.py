# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from types import SimpleNamespace
from xml.etree import ElementTree

from catkin_pkg.package import parse_package_string
from ros_buildfarm import release_job, trigger_job
from ros_buildfarm.config.release_build_file import ReleaseBuildFile
from ros_buildfarm.scripts.release import generate_release_maintenance_jobs as maint


def _pkg(name, deps=()):
    dep_tags = ''.join('<depend>%s</depend>' % d for d in deps)
    return parse_package_string(
        '<package format="3"><name>%s</name><version>1.0.0</version>'
        '<description>d</description><maintainer email="m@example.org">m</maintainer>'
        '<license>Apache-2.0</license>%s</package>' % (name, dep_tags))


def test_configure_release_jobs_slice_induced_waves_and_repo_overrides(monkeypatch, tmp_path):
    bf = ReleaseBuildFile('default', {
        'type': 'release-build', 'version': 2,
        'targets': {'ubuntu': {'resolute': {'amd64': None}}},
        'target_repository': 'http://repo/ubuntu/building',
        'upload_credential_id': 'jenkins-agent',
        'abi_incompatibility_assumed': True,
        'skip_ignored_packages': True,
        'pipeline_jobs': True,
        'orchestration_mode': 'reverse-trigger',
        'docker_mode': 'shared-generator-and-base',
        'docker_base_image_override': 'registry:5000/ros-buildfarm/binarydeb-base-lyrical-amd64',
        'prebaked_base_image': True,
        'ros_buildfarm_repository_url': 'git://repo/ros_buildfarm.git',
        'ros_buildfarm_repository_version': 'rossif/lyrical-pipelines-iter2',
        'slice_packages': ['ament_package', 'rcutils', 'rclcpp'],
        'repositories': {'urls': ['http://repo/ubuntu/building'], 'keys': ['KEY0']},
    })
    cfg = SimpleNamespace(
        jenkins_url='http://jenkins:8080',
        rosdistro_index_url='http://repo/rosdistro/index-v4.yaml',
        git_ssh_credential_id=None,
        notify_emails=[],
        prerequisites={'debian_repositories': ['http://repo/ubuntu/building'], 'debian_repository_keys': ['KEY0']},
        distributions={'lyrical': {}},
    )
    pkgs = {
        'ament_package': _pkg('ament_package'),
        'ext_mid': _pkg('ext_mid', ['ament_package']),
        'rcutils': _pkg('rcutils', ['ext_mid']),
        'rclcpp': _pkg('rclcpp', ['rcutils']),
    }
    rel_repo = SimpleNamespace(version='1.0.0-1', url='https://github.com/ros2/rcutils.git', package_names=list(pkgs))
    dist = SimpleNamespace(
        release_packages={n: SimpleNamespace(repository_name='r') for n in pkgs},
        repositories={'r': SimpleNamespace(release_repository=rel_repo)},
    )
    monkeypatch.setattr(release_job, 'get_config_index', lambda _u: cfg)
    monkeypatch.setattr(release_job, 'get_release_build_files', lambda _c, _d: {'default': bf})
    monkeypatch.setattr(release_job, 'get_index', lambda _u: SimpleNamespace(distributions={'lyrical': {'distribution_type': 'ros2'}}))
    monkeypatch.setattr(release_job, 'get_distribution_file', lambda *_a: dist)
    monkeypatch.setattr(release_job, '_get_and_parse_distribution_cache', lambda *_a, **_kw: pkgs)
    monkeypatch.setattr(release_job, 'configure_release_views', lambda *_a, **_kw: {'Lsrc_uR': '<v/>', 'Lbin_uR64': '<v/>'})

    groovy_out = tmp_path / 'reconfigure_jobs.groovy'
    release_job.configure_release_jobs('http://repo/index.yaml', 'lyrical', 'default', groovy_script=str(groovy_out))
    job_files = {p.name.split(' ', 1)[1]: p.read_text(encoding='utf-8') for p in (tmp_path / 'job_configs').iterdir()}

    assert 'Lbin_uR64__ext_mid__ubuntu_resolute_amd64__binary' not in job_files
    rcutils_root = ElementTree.fromstring(job_files['Lbin_uR64__rcutils__ubuntu_resolute_amd64__binary'])
    assert rcutils_root.find('./disabled').text == 'false'
    upstreams = rcutils_root.find('.//upstreamProjects').text.split(',')
    assert 'Lbin_uR64__ament_package__ubuntu_resolute_amd64__binary' in upstreams
    assert all('ext_mid' not in u for u in upstreams)

    assert 'Lrel_prepare-base-images' in job_files
    wave_script = ElementTree.fromstring(job_files['Lrel_pipeline-trigger-wave']).find('./definition/script').text
    assert ("[['Lbin_uR64__ament_package__ubuntu_resolute_amd64__binary'], "
            "['Lbin_uR64__rcutils__ubuntu_resolute_amd64__binary'], "
            "['Lbin_uR64__rclcpp__ubuntu_resolute_amd64__binary']]") in wave_script
    assert 'refreshAmentAfterWave: null' in wave_script

    args = SimpleNamespace(config_url='http://repo/index.yaml', rosdistro_name='lyrical', release_build_name='default')
    reconf_xml = maint.get_reconfigure_jobs_job_config(args, cfg, bf)
    assert 'git://repo/ros_buildfarm.git' in reconf_xml

    monkeypatch.setattr(trigger_job, 'get_config_index', lambda _u: cfg)
    monkeypatch.setattr(trigger_job, 'get_release_build_files', lambda _c, _d: {'default': bf})
    monkeypatch.setattr(trigger_job, 'get_index', lambda _u: None)
    monkeypatch.setattr(trigger_job, 'get_cached_distribution', lambda *_a: dist)
    trig_groovy = tmp_path / 'trigger.groovy'
    trigger_job.trigger_release_jobs('http://repo/index.yaml', 'lyrical', 'default', False, True, '/tmp/c', groovy_script=str(trig_groovy))
    assert 'ext_mid' not in trig_groovy.read_text(encoding='utf-8')


def test_ament_base_override_precedence_and_wave_refresh_wiring(monkeypatch, tmp_path):
    bf = ReleaseBuildFile('default', {
        'type': 'release-build', 'version': 2, 'abi_incompatibility_assumed': True,
        'targets': {'ubuntu': {'resolute': {'amd64': None}}}, 'skip_ignored_packages': True,
        'target_repository': 'http://repo/ubuntu/building', 'upload_credential_id': 'jenkins-agent',
        'pipeline_jobs': True, 'orchestration_mode': 'wave-orchestrator', 'docker_mode': 'ament-base',
        'docker_base_image_override': 'registry:5000/ros-buildfarm/binarydeb-base-lyrical-amd64',
        'prebaked_base_image': True, 'ros_buildfarm_repository_url': 'git://repo/ros_buildfarm.git',
        'ros_buildfarm_repository_version': 'rossif/lyrical-pipelines-iter2',
        'slice_packages': ['ament_package', 'ament_cmake_core', 'ament_cmake', 'rcutils', 'rclcpp'],
        'repositories': {'urls': ['http://repo/ubuntu/building'], 'keys': ['KEY0']},
    })
    cfg = SimpleNamespace(
        jenkins_url='http://jenkins:8080', rosdistro_index_url='http://repo/rosdistro/index-v4.yaml',
        git_ssh_credential_id=None, notify_emails=[], distributions={'lyrical': {}},
        prerequisites={'debian_repositories': ['http://repo/ubuntu/building'], 'debian_repository_keys': ['KEY0']},
    )
    pkgs = {
        'ament_package': _pkg('ament_package'), 'ament_cmake_core': _pkg('ament_cmake_core', ['ament_package']),
        'ament_cmake': _pkg('ament_cmake', ['ament_cmake_core']), 'ament_cmake_ros': _pkg('ament_cmake_ros', ['ament_cmake']),
        'rcutils': _pkg('rcutils', ['ament_cmake_ros']), 'rclcpp': _pkg('rclcpp', ['rcutils']),
    }
    rel_repo = SimpleNamespace(version='1.0.0-1', url='https://github.com/ros2/rcutils.git', package_names=list(pkgs))
    dist = SimpleNamespace(
        release_packages={n: SimpleNamespace(repository_name='r') for n in pkgs},
        repositories={'r': SimpleNamespace(release_repository=rel_repo)},
    )
    for attr, val in (
        ('get_config_index', lambda _u: cfg), ('get_release_build_files', lambda _c, _d: {'default': bf}),
        ('get_index', lambda _u: SimpleNamespace(distributions={'lyrical': {'distribution_type': 'ros2'}})),
        ('get_distribution_file', lambda *_a: dist), ('_get_and_parse_distribution_cache', lambda *_a, **_kw: pkgs),
        ('configure_release_views', lambda *_a, **_kw: {'Lsrc_uR': '<v/>', 'Lbin_uR64': '<v/>'}),
    ):
        monkeypatch.setattr(release_job, attr, val)

    release_job.configure_release_jobs('http://repo/index.yaml', 'lyrical', 'default', groovy_script=str(tmp_path / 'r.groovy'))
    jobs = {p.name.split(' ', 1)[1]: p.read_text(encoding='utf-8') for p in (tmp_path / 'job_configs').iterdir()}

    for pre_ament in ('ament_package', 'ament_cmake_core', 'ament_cmake'):
        script = ElementTree.fromstring(jobs['Lbin_uR64__%s__ubuntu_resolute_amd64__binary' % pre_ament]).find('./definition/script').text
        assert "dockerBaseImageOverride: 'registry:5000/ros-buildfarm/binarydeb-base-lyrical-amd64'" in script
    for post_ament in ('rcutils', 'rclcpp'):
        script = ElementTree.fromstring(jobs['Lbin_uR64__%s__ubuntu_resolute_amd64__binary' % post_ament]).find('./definition/script').text
        assert "dockerBaseImageOverride: 'registry:5000/ros-buildfarm/ament-base-lyrical-amd64'" in script

    prep_root = ElementTree.fromstring(jobs['Lrel_prepare-base-images'])
    assert [n.text for n in prep_root.findall('.//hudson.model.BooleanParameterDefinition/name')] == ['ament_only', 'skip_cleanup']
    assert "amentBaseImage: 'registry:5000/ros-buildfarm/ament-base-lyrical-amd64:resolute'" in prep_root.find('./definition/script').text
    wave_script = ElementTree.fromstring(jobs['Lrel_pipeline-trigger-wave']).find('./definition/script').text
    assert "prepareBaseImagesJobName: 'Lrel_prepare-base-images'" in wave_script and 'refreshAmentAfterWave: 2' in wave_script
