<flow-definition plugin="workflow-job">
  <actions/>
  <description>Generated at @ESCAPE(now_str) from template '@ESCAPE(vars().get('source_template_name') or template_name)'@
@[if vars().get('disabled')]
but disabled since the package is blacklisted (or not whitelisted) in the configuration file@
@[end if]@
@ </description>
  <keepDependencies>false</keepDependencies>
  <properties>
@(SNIPPET(
    'property_log-rotator',
    days_to_keep=730,
    num_to_keep=10,
    artifact_num_to_keep=2,
))@
@[if vars().get('github_url')]@
@(SNIPPET(
    'property_github-project',
    project_url=github_url,
))@
@[end if]@
@[if vars().get('job_priority') is not None]@
@(SNIPPET(
    'property_job-priority',
    priority=job_priority,
))@
@[end if]@
    <org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty/>
    <org.jenkinsci.plugins.workflow.job.properties.DurabilityHintJobProperty>
      <hint>SURVIVABLE_NONATOMIC</hint>
    </org.jenkinsci.plugins.workflow.job.properties.DurabilityHintJobProperty>
@[if vars().get('parameters')]@
@(SNIPPET(
    'property_parameters-definition',
    parameters=parameters,
))@
@[end if]@
@[if vars().get('upstream_projects') and vars().get('orchestration_mode') == 'reverse-trigger']@
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>
@(SNIPPET(
    'trigger_reverse-build',
    upstream_projects=upstream_projects,
))@
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
@[end if]@
  </properties>
@{
pipeline_script = "@Library(%s) _\n%s(%s)\n" % (
    GROOVY(pipeline_shared_library),
    entrypoint_name,
    GROOVY(entrypoint_config),
)
}@
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>@ESCAPE(pipeline_script)</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>@('true' if vars().get('disabled') else 'false')</disabled>
</flow-definition>
