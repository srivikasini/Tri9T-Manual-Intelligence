"""Deterministic Mock LLM Provider with failure injection capabilities."""
import json
import re
from typing import Dict, Any, Optional, List
from app.llm.base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock LLM provider that synthesizes realistic, grounded QA test ideas
    based on the provided source content, without network or API costs.
    """

    def __init__(
        self,
        failure_mode: Optional[str] = None,
        recover_on_retry: bool = False
    ):
        self.failure_mode = failure_mode
        self.recover_on_retry = recover_on_retry
        self.call_count = 0

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "model": "grounded-rule-synthesizer-v1",
            "deterministic": True,
            "simulated_mode": self.failure_mode
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.call_count += 1

        # Failure injection handling
        if self.failure_mode:
            should_fail = True
            if self.recover_on_retry and self.call_count > 1:
                should_fail = False

            if should_fail:
                if self.failure_mode == "TIMEOUT":
                    raise TimeoutError("Mock LLM request timed out after 30.0s")
                elif self.failure_mode == "PROVIDER_ERROR":
                    raise RuntimeError("Mock LLM upstream service returned 503 Service Unavailable")
                elif self.failure_mode == "MALFORMED_JSON":
                    return '{"test_cases": [{"test_id": "TC-01", "test_objective": "Malformed JSON output...'
                elif self.failure_mode == "INVALID_COUNT":
                    # Returns only 2 test cases (violates min 3)
                    return json.dumps({
                        "test_cases": [
                            {
                                "test_id": "TC-01",
                                "test_objective": "Verify power-on state",
                                "preconditions": ["Device equipped with fresh batteries"],
                                "steps": ["Hold power button for 1s"],
                                "expected_result": "Screen activates",
                                "source_references": ["3.1"]
                            },
                            {
                                "test_id": "TC-02",
                                "test_objective": "Verify cuff deflation",
                                "preconditions": ["Cuff connected"],
                                "steps": ["Start test and observe"],
                                "expected_result": "Deflates smoothly",
                                "source_references": ["3.2"]
                            }
                        ]
                    })
                elif self.failure_mode == "MISSING_FIELD":
                    return json.dumps({
                        "test_cases": [
                            {
                                "test_id": "TC-01",
                                "test_objective": "Verify overpressure auto-deflate",
                                "preconditions": ["Pressure exceeds 299 mmHg"],
                                "steps": ["Inject 305 mmHg pressure"],
                                # missing expected_result!
                                "source_references": ["4.1"]
                            },
                            {
                                "test_id": "TC-02",
                                "test_objective": "Verify motion artifact detection",
                                "preconditions": ["Active measurement in progress"],
                                "steps": ["Move arm vigorously"],
                                "expected_result": "Display error code E2 and abort",
                                "source_references": ["4.2"]
                            },
                            {
                                "test_id": "TC-03",
                                "test_objective": "Verify Bluetooth sync rejection",
                                "preconditions": ["Bluetooth disabled on host"],
                                "steps": ["Attempt sync"],
                                "expected_result": "Displays E6 sync failure",
                                "source_references": ["4.2"]
                            }
                        ]
                    })

        # Normal deterministic generation grounded in prompt context
        test_cases: List[Dict[str, Any]] = []

        # Analyze context
        lower_prompt = prompt.lower()

        # Test Case 1: Overpressure / Error Behavior
        if "overpressure" in lower_prompt or "299" in lower_prompt or "e3" in lower_prompt:
            test_cases.append({
                "test_id": "TC-01",
                "test_objective": "Verify overpressure protection triggers safety auto-deflation within specified time threshold",
                "preconditions": [
                    "CardioTrack CT-200 connected to pneumatic test fixture with calibrated pressure sensor",
                    "Device powered on with User 1 profile active"
                ],
                "steps": [
                    "Initiate blood pressure measurement sequence by pressing Start button",
                    "Simulate cuff occlusion causing pneumatic pressure to exceed 299 mmHg",
                    "Measure duration between overpressure threshold exceedance and valve release",
                    "Observe device display for generated error code"
                ],
                "expected_result": "Device must immediately abort inflation, trigger auto-deflate valve within 1.5-2.0 seconds, and display error code E3.",
                "source_references": ["Section 4.1", "Section 4.2"]
            })

        # Test Case 2: Motion Artifact / Error Code E2
        if "motion" in lower_prompt or "e2" in lower_prompt or "artifact" in lower_prompt or "operation" in lower_prompt:
            test_cases.append({
                "test_id": "TC-02",
                "test_objective": "Verify motion artifact detection halts measurement and instructs user to retry",
                "preconditions": [
                    "CT-200 standard cuff fitted snugly around human subject or simulated arm mannequin",
                    "Device powered on in resting position"
                ],
                "steps": [
                    "Press Start button to initiate cuff inflation",
                    "During oscillometric measurement cycle (at approximately 80 mmHg cuff pressure), induce continuous arm motion for 3 seconds",
                    "Observe system response and display output"
                ],
                "expected_result": "System detects motion artifact, aborts measurement, releases cuff pressure, displays error code E2, and prompts retry.",
                "source_references": ["Section 4.2", "Section 3.2"]
            })

        # Test Case 3: Battery and Power Consumption / Auto Shutoff
        if "battery" in lower_prompt or "power" in lower_prompt or "auto shutoff" in lower_prompt or "shutoﬀ" in lower_prompt:
            test_cases.append({
                "test_id": "TC-03",
                "test_objective": "Verify automatic shutoff engages after 60 seconds of inactivity to conserve battery power",
                "preconditions": [
                    "CT-200 powered by four fresh AA alkaline batteries",
                    "Device powered on and idle at main profile selection screen"
                ],
                "steps": [
                    "Power on device by pressing power button for one second",
                    "Leave device unattended with no button presses or cuff connection",
                    "Record time elapsed until display turns off completely"
                ],
                "expected_result": "Device automatically powers down after exactly 60 seconds of inactivity.",
                "source_references": ["Section 3.4", "Section 2.1.1.1"]
            })

        # Test Case 4: Bluetooth Data Sync or Error E6
        if "bluetooth" in lower_prompt or "sync" in lower_prompt or "e6" in lower_prompt or "export" in lower_prompt:
            test_cases.append({
                "test_id": "TC-04",
                "test_objective": "Verify Bluetooth communication failure is indicated by error code E6 without corrupting stored records",
                "preconditions": [
                    "At least 5 valid measurement records stored in CT-200 local memory",
                    "CardioTrack companion mobile app opened with Bluetooth disconnected"
                ],
                "steps": [
                    "Trigger manual sync command from device or application",
                    "Simulate RF interference or broken connection during packet transfer",
                    "Check device display and verify local memory integrity"
                ],
                "expected_result": "Device displays error code E6 on next sync attempt; previous local measurements remain intact in non-volatile memory.",
                "source_references": ["Section 4.2", "Section 5.2"]
            })

        # Grounded general operational tests to ensure at least 3 test cases
        fallback_pool = [
            {
                "test_objective": "Verify profile selection toggling between User 1 and User 2 prior to measurement",
                "preconditions": ["Device powered on and idle"],
                "steps": [
                    "Press profile toggle button once",
                    "Verify active profile indicator on LCD display",
                    "Initiate measurement and confirm reading saves to designated profile storage"
                ],
                "expected_result": "Display switches from User 1 to User 2 indicator, and subsequent readings persist in the selected profile memory.",
                "source_references": ["Section 3.1", "Section 5.1"]
            },
            {
                "test_objective": "Verify measurement abort upon missing or disconnected cuff (Error Code E1)",
                "preconditions": ["Device powered on with air hose detached"],
                "steps": [
                    "Press Start button without cuff connected to air jack",
                    "Observe device motor pump and display response"
                ],
                "expected_result": "Device detects open pneumatic circuit, terminates pump operation within 5 seconds, and presents error code E1.",
                "source_references": ["Section 4.2"]
            },
            {
                "test_objective": "Verify blood pressure classification display for normal measurement values",
                "preconditions": ["CT-200 cuff applied properly to resting subject"],
                "steps": [
                    "Initiate measurement and allow cuff to inflate and deflate",
                    "Record displayed systolic and diastolic pressure values",
                    "Check classification indicator segment on LCD"
                ],
                "expected_result": "When systolic is < 120 and diastolic is < 80, the display indicates Normal classification.",
                "source_references": ["Section 3.3"]
            }
        ]

        pool_idx = 0
        while len(test_cases) < 3 and pool_idx < len(fallback_pool):
            fb = fallback_pool[pool_idx]
            test_cases.append({
                "test_id": f"TC-0{len(test_cases)+1}",
                "test_objective": fb["test_objective"],
                "preconditions": fb["preconditions"],
                "steps": fb["steps"],
                "expected_result": fb["expected_result"],
                "source_references": fb["source_references"]
            })
            pool_idx += 1

        # Ensure exactly 3 to 4 test cases
        trimmed_cases = test_cases[:4]

        return json.dumps({"test_cases": trimmed_cases}, indent=2)
