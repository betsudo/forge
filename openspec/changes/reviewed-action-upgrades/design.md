# Pinned actions and unchanged trust boundaries

Pin verified official commits for checkout 7.0.1, upload-artifact 7.0.2,
deploy-pages 5.0.1 and upload-pages-artifact 5.0.0. Hosted ubuntu-24.04 supports
the Node 24 action runtime. Keep persist-credentials:false and the exact trusted
base SHA in pull_request_target. Never enable the unsafe fork checkout escape
hatch. Artifact names, paths, retention and hidden-file behavior remain unchanged;
explicit archive:true preserves download/extraction compatibility for v7 uploads.
Pages upload remains github-pages and deployment remains manual with existing
pages/id-token permissions. PR CI cannot qualify actual Pages deployment or the
new trusted-base checkout before merge; report those limits rather than dispatch.
