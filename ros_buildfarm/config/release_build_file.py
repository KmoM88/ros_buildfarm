# Copyright 2013-2016 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .build_file import BuildFile

VALID_ORCHESTRATION_MODES = ('reverse-trigger', 'wave-orchestrator')
VALID_DOCKER_MODES = ('baseline', 'shared-generator', 'shared-generator-and-base')


def _parse_bool(data, key, default):
    if key not in data:
        return default
    val = data[key]
    if not isinstance(val, bool):
        raise ValueError("'%s' must be a boolean, got %r" % (key, val))
    return val


def _parse_optional_str(data, key, default=None):
    if key not in data or data[key] is None:
        if default is not None and key in data and data[key] is None:
            raise ValueError("'%s' must be a non-empty string" % key)
        return default
    val = data[key]
    if not isinstance(val, str) or not val.strip():
        raise ValueError("'%s' must be a non-empty string, got %r" % (key, val))
    return val


class ReleaseBuildFile(BuildFile):

    _type = 'release-build'

    def __init__(self, name, data):  # noqa: D107
        assert 'type' in data, \
            "Expected file type is '%s'" % ReleaseBuildFile._type
        assert data['type'] == ReleaseBuildFile._type, \
            "Expected file type is '%s', not '%s'" % \
            (ReleaseBuildFile._type, data['type'])

        assert 'version' in data, \
            ("Release build file for '%s' lacks required version " +
             "information") % self.name
        assert int(data['version']) in [1, 2], \
            ("Unable to handle '%s' format version '%d', please update " +
             "rosdistro (e.g. on Ubuntu/Debian use: sudo apt update && " +
             "sudo apt install --only-upgrade python-rosdistro)") % \
            (ReleaseBuildFile._type, int(data['version']))
        self.version = int(data['version'])

        super(ReleaseBuildFile, self).__init__(name, data)

        assert len(self.targets) > 0

        self.abi_incompatibility_assumed = None
        if 'abi_incompatibility_assumed' in data:
            self.abi_incompatibility_assumed = \
                bool(data['abi_incompatibility_assumed'])

        self.jenkins_binary_job_label = None
        if 'jenkins_binary_job_label' in data:
            self.jenkins_binary_job_label = data['jenkins_binary_job_label']
        self.jenkins_binary_job_priority = None
        if 'jenkins_binary_job_priority' in data:
            self.jenkins_binary_job_priority = \
                int(data['jenkins_binary_job_priority'])
        self.jenkins_binary_job_timeout = None
        if 'jenkins_binary_job_timeout' in data:
            self.jenkins_binary_job_timeout = \
                int(data['jenkins_binary_job_timeout'])

        self.jenkins_source_job_label = None
        if 'jenkins_source_job_label' in data:
            self.jenkins_source_job_label = data['jenkins_source_job_label']
        self.jenkins_source_job_priority = None
        if 'jenkins_source_job_priority' in data:
            self.jenkins_source_job_priority = \
                int(data['jenkins_source_job_priority'])
        self.jenkins_source_job_timeout = None
        if 'jenkins_source_job_timeout' in data:
            self.jenkins_source_job_timeout = \
                int(data['jenkins_source_job_timeout'])

        self.jenkins_binary_job_weight_overrides = {}
        if 'jenkins_binary_job_weight_overrides' in data:
            self.jenkins_binary_job_weight_overrides = data['jenkins_binary_job_weight_overrides']
            assert isinstance(self.jenkins_binary_job_weight_overrides, dict)

        self.package_whitelist = []
        if 'package_whitelist' in data and data['package_whitelist']:
            self.package_whitelist = data['package_whitelist']
            assert isinstance(self.package_whitelist, list)
        self.package_blacklist = []
        if 'package_blacklist' in data and data['package_blacklist']:
            self.package_blacklist = data['package_blacklist']
            assert isinstance(self.package_blacklist, list)
        self.package_ignore_list = []
        if 'package_ignore_list' in data and data['package_ignore_list']:
            self.package_ignore_list = data['package_ignore_list']
            assert isinstance(self.package_ignore_list, list)
        self.skip_ignored_packages = None
        if 'skip_ignored_packages' in data:
            self.skip_ignored_packages = \
                bool(data['skip_ignored_packages'])

        self.sync_package_count = None
        self.sync_package_percent = None
        self.sync_packages = []
        if 'sync' in data:
            if 'package_percent' in data['sync']:
                percent = float(data['sync']['package_percent'])
                assert percent >= 0.0 and percent <= 100.0
                self.sync_package_percent = percent / 100.0
            if 'package_count' in data['sync']:
                self.sync_package_count = int(data['sync']['package_count'])
            if 'packages' in data['sync'] and data['sync']['packages']:
                self.sync_packages = data['sync']['packages']
                assert isinstance(self.sync_packages, list)

        self.target_queue = None
        if 'target_queue' in data:
            self.target_queue = str(data['target_queue'])
        assert 'target_repository' in data
        self.target_repository = data['target_repository']

        assert 'upload_credential_id' in data
        self.upload_credential_id = data['upload_credential_id']

        self.upload_host = None
        if 'upload_host' in data:
            self.upload_host = data['upload_host']

        self.include_group_dependencies = False
        self.include_test_dependencies = True
        self.run_package_tests = True
        if data.get('package_dependency_behavior'):
            assert isinstance(data['package_dependency_behavior'], dict)
            if 'include_group_dependencies' in data['package_dependency_behavior']:
                self.include_group_dependencies = \
                    bool(data['package_dependency_behavior']['include_group_dependencies'])
            if 'include_test_dependencies' in data['package_dependency_behavior']:
                self.include_test_dependencies = \
                    bool(data['package_dependency_behavior']['include_test_dependencies'])
            if 'run_package_tests' in data['package_dependency_behavior']:
                self.run_package_tests = \
                    bool(data['package_dependency_behavior']['run_package_tests'])

        self.pipeline_jobs = _parse_bool(data, 'pipeline_jobs', False)
        self.pipeline_shared_library = _parse_optional_str(
            data, 'pipeline_shared_library', 'ros-buildfarm-pipelines@main')
        self.orchestration_mode = _parse_optional_str(
            data, 'orchestration_mode', 'reverse-trigger')
        if self.orchestration_mode not in VALID_ORCHESTRATION_MODES:
            raise ValueError("Unsupported 'orchestration_mode': %r" % (self.orchestration_mode,))

        self.docker_mode = _parse_optional_str(data, 'docker_mode', 'baseline')
        if self.docker_mode not in VALID_DOCKER_MODES:
            raise ValueError("Unsupported 'docker_mode': %r" % (self.docker_mode,))

        self.docker_base_image_override = _parse_optional_str(data, 'docker_base_image_override')
        if self.docker_base_image_override is not None:
            last_segment = self.docker_base_image_override.rsplit('/', 1)[-1]
            if ':' in last_segment or '@' in last_segment:
                raise ValueError(
                    "'docker_base_image_override' must not include tag/digest: %r" %
                    (self.docker_base_image_override,))

        self.prebaked_base_image = _parse_bool(data, 'prebaked_base_image', False)
        self.ros_buildfarm_repository_url = _parse_optional_str(
            data, 'ros_buildfarm_repository_url')
        self.ros_buildfarm_repository_version = _parse_optional_str(
            data, 'ros_buildfarm_repository_version')

        self.slice_packages = None
        if 'slice_packages' in data and data['slice_packages'] is not None:
            raw_slice = data['slice_packages']
            if not isinstance(raw_slice, list) or not raw_slice or not all(
                isinstance(p, str) and p.strip() for p in raw_slice
            ):
                raise ValueError("'slice_packages' must be a non-empty list of strings")
            self.slice_packages = list(raw_slice)

    def filter_packages(self, package_names):
        res = set(package_names)
        if self.package_whitelist:
            res &= set(self.package_whitelist)
        res -= set(self.package_blacklist)
        res -= set(self.package_ignore_list)
        return res
