import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('cluster',Path(__file__).parents[1]/'scripts/cluster.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class ClusterTests(unittest.TestCase):
    def test_kubectl_uses_isolated_config_and_context(self):
        cmd=c.kubectl('get','nodes')
        self.assertIn('--kubeconfig',cmd)
        self.assertEqual(cmd[cmd.index('--context')+1],'kind-wattshift')
    def test_missing_tools_prevent_cluster_mutation(self):
        with patch.object(c.shutil,'which',return_value=None),patch.object(c,'command') as run:
            with self.assertRaisesRegex(RuntimeError,'Missing tools'):c.up()
            run.assert_not_called()
    def test_existing_cluster_is_not_recreated(self):
        with tempfile.TemporaryDirectory() as d:
            kube=Path(d)/'kubeconfig';kube.touch()
            def response(args,**kwargs):
                return 'wattshift\nother-cluster' if args==['kind','get','clusters'] else ''
            with patch.object(c,'KUBECONFIG',kube),patch.object(c,'doctor'),patch.object(c,'verify'),patch.object(c,'command',side_effect=response) as run:
                c.up()
                self.assertFalse(any(x.args[0][:3]==['kind','create','cluster'] for x in run.call_args_list))
                self.assertTrue(any(x.args[0][:3]==['kind','export','kubeconfig'] for x in run.call_args_list))
    def test_missing_config_cannot_pass_gate(self):
        with tempfile.TemporaryDirectory() as d,patch.object(c,'KUBECONFIG',Path(d)/'missing'):
            with self.assertRaises(RuntimeError):c.verify()
    def test_wrong_cluster_cannot_pass_gate(self):
        with tempfile.TemporaryDirectory() as d:
            kube=Path(d)/'k';kube.touch();evidence=Path(d)/'e'
            node={'items':[{'metadata':{'name':'other-control-plane'}}]}
            def response(args,**kwargs):return json.dumps(node) if 'nodes' in args and 'get' in args else ''
            with patch.object(c,'KUBECONFIG',kube),patch.object(c,'EVIDENCE',evidence),patch.object(c,'command',side_effect=response):
                with self.assertRaisesRegex(RuntimeError,'identity'):c.verify()
                self.assertFalse(evidence.exists())
    def test_failed_verification_clears_old_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            kube=Path(d)/'k';kube.touch();ev=Path(d)/'e';ev.write_text('stale success')
            with patch.object(c,'KUBECONFIG',kube),patch.object(c,'EVIDENCE',ev),patch.object(c,'command',side_effect=RuntimeError('not ready')):
                with self.assertRaises(RuntimeError):c.verify()
                self.assertFalse(ev.exists())
    def test_success_writes_evidence_only_after_all_checks(self):
        with tempfile.TemporaryDirectory() as d:
            kube=Path(d)/'k';kube.touch();ev=Path(d)/'e'
            node={'items':[{'metadata':{'name':'wattshift-control-plane'},'status':{'nodeInfo':{'kubeletVersion':'v1.35.0'}}}]}
            def response(args,**kwargs):
                if args[:3]==['kind','get','nodes']:return 'wattshift-control-plane'
                if 'get' in args and 'nodes' in args:return json.dumps(node)
                if 'namespace' in args:return json.dumps({'status':{'phase':'Active'}})
                return ''
            with patch.object(c,'KUBECONFIG',kube),patch.object(c,'EVIDENCE',ev),patch.object(c,'command',side_effect=response):
                c.verify()
                self.assertEqual(json.loads(ev.read_text())['status'],'runtime_verified')

    def test_down_is_scoped_to_named_cluster(self):
        with tempfile.TemporaryDirectory() as d,patch.object(c,'KUBECONFIG',Path(d)/'k'),patch.object(c,'EVIDENCE',Path(d)/'e'),patch.object(c,'command') as run:
            c.down()
            args=run.call_args.args[0]
            self.assertEqual(args[args.index('--name')+1],'wattshift')
            self.assertNotIn('--all',args)

if __name__=='__main__':unittest.main()
