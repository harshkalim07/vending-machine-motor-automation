#!/usr/bin/env python3
"""
Unit test for the Security Check Math Solver & UI Parser.
Tests various arithmetic problem formats and XML node extractions.
"""

import re
import xml.etree.ElementTree as ET

def solve_security_math(text):
    """Extract and solve arithmetic question (supports +, -, *)"""
    m = re.search(r"(\d+)\s*([\+\-\*])\s*(\d+)", text)
    if m:
        n1 = int(m.group(1))
        op = m.group(2)
        n2 = int(m.group(3))
        if op == "+":
            return n1 + n2
        elif op == "-":
            return n1 - n2
        elif op == "*":
            return n1 * n2
    return None

def test_math_equations():
    test_cases = [
        ("What is 25+ 38?", 63),       # The exact equation from your video!
        ("What is 25 + 38?", 63),
        ("What is 14 + 82?", 96),
        ("What is 7 + 9?", 16),
        ("What is 50 - 18?", 32),
        ("What is 8 * 7?", 56),
        ("25+38", 63),
    ]

    print("Running Security Math Solver Unit Tests:")
    all_passed = True
    for expr, expected in test_cases:
        res = solve_security_math(expr)
        passed = (res == expected)
        mark = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {mark} | '{expr}' -> Output: {res} (Expected: {expected})")
        if not passed:
            all_passed = False

    return all_passed

def test_mock_ui_xml():
    mock_xml = """
    <hierarchy rotation="0">
      <node class="android.widget.FrameLayout" bounds="[0,0][1080,1920]">
        <node class="android.widget.TextView" text="Security Check" bounds="[200,600][880,700]" />
        <node class="android.widget.TextView" text="What is 25+ 38?" bounds="[200,720][880,800]" />
        <node class="android.widget.EditText" text="" bounds="[250,820][830,920]" />
        <node class="android.widget.Button" text="CANCEL" bounds="[250,950][520,1050]" />
        <node class="android.widget.Button" text="VERIFY" bounds="[560,950][830,1050]" />
      </node>
    </hierarchy>
    """
    root = ET.fromstring(mock_xml)
    question_node = None
    for node in root.iter("node"):
        t = node.attrib.get("text", "")
        if "What is" in t or re.search(r"\d+\s*[\+\-\*]\s*\d+", t):
            question_node = node
            break

    assert question_node is not None, "Failed to find question node in XML"
    ans = solve_security_math(question_node.attrib.get("text"))
    assert ans == 63, f"Expected 63, got {ans}"
    print("\n✅ PASS | Mock Android UI XML hierarchy parsed successfully! Answer = 63")

if __name__ == "__main__":
    test_math_equations()
    test_mock_ui_xml()
