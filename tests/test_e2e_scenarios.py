from pathlib import Path
import copy
import zipfile

from scripts.lib.e2e_analysis import analyze_repository
from scripts.lib.zip_workflow import prepare_workspace, write_portable_state, package_workspace, load_portable_state
from scripts.lib.step_control import initialize_progress, apply_user_action, record_execution_result
from scripts.lib.github_read_workflow import GitHubRepositoryRef, GitHubRepositorySnapshot, materialize_snapshot, build_github_read_context
from scripts.lib.github_write_workflow import initialize_github_write_state, plan_write_target, record_pr_created, record_step_commit

FIXTURES = Path(__file__).parent / 'fixtures' / 'e2e'


def ids(result):
    return {f['id'] for f in result['findings']}


def test_clean_repository_has_no_must_fix():
    result = analyze_repository(FIXTURES/'clean-node')
    assert not [f for f in result['findings'] if f['classification'] == 'must-fix']
    assert '# Repository analysis' in result['report_markdown']


def test_react_stale_readme_detects_package_manager_mismatch():
    result = analyze_repository(FIXTURES/'stale-react-readme')
    assert any(f['area']=='readme' and 'package manager' in f['title'].lower() for f in result['findings'])
    assert result['plan_model']['steps']


def test_java_wrong_documented_version_is_detected():
    result = analyze_repository(FIXTURES/'java-wrong-version')
    assert any(f['area']=='readme' and 'java' in f['title'].lower() for f in result['findings'])


def test_fullstack_partial_ci_detects_uncovered_backend():
    result = analyze_repository(FIXTURES/'partial-ci-fullstack')
    assert 'fullstack' in result['inventory']['project_types']
    assert any(f['area']=='github-actions' and ('backend' in f['summary'].lower() or 'maven' in f['summary'].lower()) for f in result['findings'])


def test_repository_without_license_is_consider_not_hard_error():
    result = analyze_repository(FIXTURES/'no-license')
    license_findings=[f for f in result['findings'] if f['area']=='license']
    assert license_findings
    assert all(f['classification'] != 'must-fix' for f in license_findings)


def test_readme_license_conflict_requires_decision():
    result = analyze_repository(FIXTURES/'license-conflict')
    conflicts=[f for f in result['findings'] if f['area']=='license' and f['classification']=='must-fix']
    assert conflicts and any(f['decision_required'] for f in conflicts)


def test_clear_temporary_files_and_ambiguous_old_file_are_distinguished():
    temp = analyze_repository(FIXTURES/'temporary-files')
    assert any(f['area']=='repository-hygiene' and f['classification'] in {'must-fix','recommended'} for f in temp['findings'])
    ambiguous = analyze_repository(FIXTURES/'ambiguous-old-file')
    old=[f for f in ambiguous['findings'] if f['area']=='repository-hygiene' and 'migration-old.md' in str(f.get('evidence'))]
    assert not old or all(f['classification'] != 'must-fix' or f.get('decision_required') for f in old)


def test_zip_flow_preserves_progress_across_multiple_steps(tmp_path):
    source=tmp_path/'repo.zip'
    root=FIXTURES/'stale-react-readme'
    with zipfile.ZipFile(source,'w') as zf:
        for p in root.rglob('*'):
            if p.is_file(): zf.write(p, f'repo/{p.relative_to(root).as_posix()}')
    ws=prepare_workspace(source, tmp_path/'work')
    analysis=analyze_repository(ws.repository_root, 'repo')
    plan=analysis['plan_model']; progress=initialize_progress(plan)
    first=next(s for s in progress['steps'] if s['status']=='planned')
    apply_user_action(plan, progress, 'do', first['id'])
    record_execution_result(plan, progress, first['id'], success=True, verification_status='not-verified')
    write_portable_state(ws.repository_root, analysis_md=analysis['report_markdown'], plan_md=analysis['plan_markdown'], progress_md='progress', analysis=analysis['report_model'], plan=plan, progress=progress)
    out=package_workspace(ws, tmp_path/'updated.zip')
    ws2=prepare_workspace(out, tmp_path/'work2')
    state=load_portable_state(ws2.repository_root)
    resumed=state['progress_json']
    assert resumed['steps'][0]['status']=='completed'
    next_planned=next((s for s in resumed['steps'] if s['status']=='planned'), None)
    if next_planned is not None:
        apply_user_action(plan, resumed, 'do', next_planned['id'])
        record_execution_result(plan, resumed, next_planned['id'], success=True, verification_status='not-verified')
        assert len([s for s in resumed['steps'] if s['status']=='completed']) >= 2
    assert (ws2.repository_root/'.repository-fixer/analysis.md').exists()


def _snapshot_from_fixture(name, prs=()):
    root=FIXTURES/name
    files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return GitHubRepositorySnapshot(GitHubRepositoryRef('example',name,f'https://github.com/example/{name}'),'main','main',files,'abc123',True,tuple(prs))


def test_github_flow_reuses_open_repository_fixer_pr(tmp_path):
    snap=_snapshot_from_fixture('stale-react-readme', [{'number':7,'state':'open','head_ref':'repository-fixer/01-step-01','base_ref':'main','title':'Repository Fixer'}])
    ws=materialize_snapshot(snap,tmp_path/'gh')
    result=analyze_repository(ws.repository_root)
    context=build_github_read_context(snap); state=initialize_github_write_state(context)
    state['active_branch']='repository-fixer/01-step-01'; state['active_pr']={'number':7,'state':'open','head_ref':'repository-fixer/01-step-01','base_ref':'main','url':None}
    target=plan_write_target(state, result['plan_model']['steps'][0]['id'], refreshed_pr={'number':7,'state':'open','head_ref':'repository-fixer/01-step-01','base_ref':'main'})
    assert target['action']=='reuse-open-pr'


def test_github_flow_creates_new_pr_after_previous_merge(tmp_path):
    snap=_snapshot_from_fixture('stale-react-readme')
    context=build_github_read_context(snap); state=initialize_github_write_state(context)
    first=plan_write_target(state,'STEP-01')
    record_pr_created(state,branch=first['branch'],sequence=first['sequence'],pr={'number':1,'state':'open','head_ref':first['branch'],'base_ref':'main'})
    record_step_commit(state,step_id='STEP-01',commit_sha='def456',message='docs: fix readme')
    after=plan_write_target(state,'STEP-02',refreshed_pr={'number':1,'state':'closed','merged':True,'head_ref':first['branch'],'base_ref':'main'},default_branch_sha='merged789')
    assert after['action']=='create-branch-and-pr'
    assert after['sequence']==2
    assert after['base_sha']=='merged789'
