@{
entrypoint_config = {
    'rosdistroIndexUrl': rosdistro_index_url,
    'rosdistroName': rosdistro_name,
    'releaseBuildName': release_build_name,
    'pkgName': pkg_name,
    'debianPkgName': debian_package_name,
    'osName': os_name,
    'osCodeName': os_code_name,
    'arch': arch,
    'repositoryUrls': repository_urls,
    'repositoryKeys': repository_keys,
    'rosBuildfarmRepoUrl': ros_buildfarm_repository.url,
    'rosBuildfarmRepoVersion': ros_buildfarm_repository.version,
    'importPackageJobName': import_package_job_name,
    'credentialId': credential_id,
    'uploadHost': vars().get('upload_host') or 'repo',
    'gitSshCredentialId': vars().get('git_ssh_credential_id'),
    'nodeLabel': node_label,
    'timeoutMinutes': timeout_minutes,
    'dockerMode': docker_mode,
}
parameters = [
    {
        'type': 'boolean',
        'name': 'skip_cleanup',
        'description': 'Skip cleanup of build artifacts',
    },
]
}@
@(TEMPLATE(
    'release/pipeline_utility_job.xml.em',
    source_template_name=template_name,
    now_str=now_str,
    disabled=disabled,
    github_url=github_url,
    job_priority=job_priority,
    parameters=parameters,
    pipeline_shared_library=pipeline_shared_library,
    entrypoint_name='rosReleaseSourceDeb',
    entrypoint_config=entrypoint_config,
))@
