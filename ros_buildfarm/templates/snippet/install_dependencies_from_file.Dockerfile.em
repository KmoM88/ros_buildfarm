@{
use_apt_cache = bool(vars().get('buildkit_apt_cache'))
run_prefix = (
    'RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked '
    'rm -f /etc/apt/apt.conf.d/docker-clean && '
    "printf 'Binary::apt::APT::Keep-Downloaded-Packages \"true\";\\n"
    "APT::Keep-Downloaded-Packages \"true\";\\n' > /etc/apt/apt.conf.d/keep-cache && "
    if use_apt_cache else 'RUN '
)
apt_subcmd = 'update-install' if use_apt_cache else 'update-install-clean'
}@
@[for install_list in install_lists]@
COPY @(install_list) .
@(run_prefix)sed '/^#.*/d' @(install_list) | xargs python3 -u /tmp/wrapper_scripts/apt.py @(apt_subcmd) -q -y -o Debug::pkgProblemResolver=yes
@[end for]@
