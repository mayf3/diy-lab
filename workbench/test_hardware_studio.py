"""Hardware Studio（PR-A）测试：项目模型校验器 + 首屏九问数据通道。

运行：python3 -m unittest discover -s workbench -p 'test_*.py'
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "hardware/check_project.py"
PROJECT = ROOT / "hardware/space-buddy-r1/project.json"


def run_validator(project=PROJECT, changed=None):
    args = [sys.executable, str(CHECKER), "--project", str(project)]
    if changed:
        args += ["--changed", changed]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}


def load_workbench():
    return json.loads((ROOT / "workbench/web/workbench.json").read_text(encoding="utf-8"))


class ProjectValidatorTests(unittest.TestCase):
    def test_real_project_passes(self):
        code, out = run_validator()
        self.assertEqual(code, 0, f"真实项目应通过校验：{out.get('failures')}")
        self.assertTrue(out["checks"]["quad_complete"])
        self.assertTrue(out["checks"]["cad_geometry_green"])
        self.assertTrue(out["checks"]["artifacts_present"])
        self.assertFalse(out["product_ready"])

    def test_quad_partial_is_rejected(self):
        import tempfile
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        # 删掉 bom 段 → 必须判违规（禁止部分声明）
        del proj["version_contract"]["revisions"]["bom"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=str(ROOT / "hardware")) as f:
            json.dump(proj, f, ensure_ascii=False)
            tmp = f.name
        code, out = run_validator(project=Path(tmp))
        Path(tmp).unlink()
        self.assertEqual(code, 2)
        self.assertFalse(out["checks"]["quad_complete"])

    def test_changed_propagates_downstream(self):
        code, out = run_validator(changed="dims.keys")
        self.assertEqual(code, 0)  # 失效传播是信息，不是失败
        stale = " ".join(out["stale_downstream"])
        self.assertIn("cad.caps", stale)
        self.assertIn("pcb.switch-footprint", stale)
        self.assertIn("STALE", stale)

    def test_unknown_change_key_is_flagged(self):
        code, out = run_validator(changed="dims.不存在的键")
        self.assertEqual(code, 2)
        self.assertTrue(any("未知变更键" in f for f in out["failures"]))

    def test_guard_blocks_premature_product_ready(self):
        import tempfile
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        proj["guard"]["product_ready"] = True   # pcb 仍为 null → 必须违规
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=str(ROOT / "hardware")) as f:
            json.dump(proj, f, ensure_ascii=False)
            tmp = f.name
        code, out = run_validator(project=Path(tmp))
        Path(tmp).unlink()
        self.assertEqual(code, 2)
        self.assertTrue(any("product_ready" in f for f in out["failures"]))


class WorkbenchHardwareCardTests(unittest.TestCase):
    """首屏九问卡：数据必须来自真实校验器，且 EDA 环境可用 ≠ 产品就绪。"""

    def setUp(self):
        self.wb = load_workbench()

    def test_hardware_section_present_and_ok(self):
        hw = self.wb.get("hardware") or {}
        self.assertTrue(hw.get("ok"), f"校验器未通过：{hw.get('error') or hw.get('failures')}")
        self.assertFalse(hw.get("product_ready"), "产品未完成不得标就绪")

    def test_nine_questions_data_available(self):
        nine = self.wb.get("hardware_next") or {}
        for key in ("looks_like", "pcb_done", "joint_verified", "factory_can",
                    "package_complete", "blockers", "next_owner", "needs_user"):
            self.assertIn(key, nine, f"九问卡缺字段：{key}")
        self.assertEqual(nine["pcb_done"], "未开始（无 R1 原生 EDA 工程）",
                         "PCB 未开始必须如实显示，EDA 环境可用不等于 PCB 完成")
        self.assertFalse(nine["package_complete"])
        owners = [o["who"] for o in nine["next_owner"]]
        self.assertIn("负责人", owners, "采购/付款必须归属负责人")

    def test_environment_ready_is_not_product_ready(self):
        env_ready = self.wb["environment"]["checks"]
        hw = self.wb["hardware"]
        # 即使某天环境全绿，产品 ready 也必须由 guard 单独决定
        self.assertIsNotNone(env_ready)
        self.assertFalse(hw.get("product_ready", True))


if __name__ == "__main__":
    unittest.main()
