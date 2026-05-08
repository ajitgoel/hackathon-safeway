"""
Unit tests for response_assembler.py.

Covers:
- Single block renders as "**{label}:**\n{response}"
- Multiple blocks are separated by a blank line and maintain input order
- Empty input list returns an empty string without error
"""

from response_assembler import assemble


class TestAssembleSingleBlock:
    def test_single_block_format(self):
        results = [{"intent": "performance_summary", "label": "Performance Summary", "response": "You did well."}]
        output = assemble(results)
        assert output == "**Performance Summary:**\nYou did well."

    def test_single_block_starts_with_bold_label(self):
        results = [{"intent": "next_week_plan", "label": "Next Week Plan", "response": "Focus on sleep."}]
        output = assemble(results)
        assert output.startswith("**Next Week Plan:**")

    def test_single_block_response_follows_label(self):
        results = [{"intent": "next_week_plan", "label": "Next Week Plan", "response": "Focus on sleep."}]
        output = assemble(results)
        assert "**Next Week Plan:**\nFocus on sleep." in output

    def test_single_block_no_trailing_blank_line(self):
        results = [{"intent": "performance_summary", "label": "Performance Summary", "response": "Good week."}]
        output = assemble(results)
        assert not output.endswith("\n\n")


class TestAssembleMultipleBlocks:
    def test_two_blocks_separated_by_blank_line(self):
        results = [
            {"intent": "performance_summary", "label": "Performance Summary", "response": "Good week."},
            {"intent": "next_week_plan", "label": "Next Week Plan", "response": "Sleep more."},
        ]
        output = assemble(results)
        assert "**Performance Summary:**\nGood week.\n\n**Next Week Plan:**\nSleep more." == output

    def test_order_preserved_first_block(self):
        results = [
            {"intent": "performance_summary", "label": "Performance Summary", "response": "First."},
            {"intent": "next_week_plan", "label": "Next Week Plan", "response": "Second."},
            {"intent": "multi_metric_deep_dive", "label": "Deep Dive", "response": "Third."},
        ]
        output = assemble(results)
        first_pos = output.index("**Performance Summary:**")
        second_pos = output.index("**Next Week Plan:**")
        third_pos = output.index("**Deep Dive:**")
        assert first_pos < second_pos < third_pos

    def test_three_blocks_contain_all_labels(self):
        results = [
            {"intent": "performance_summary", "label": "Performance Summary", "response": "A"},
            {"intent": "next_week_plan", "label": "Next Week Plan", "response": "B"},
            {"intent": "multi_metric_deep_dive", "label": "Deep Dive", "response": "C"},
        ]
        output = assemble(results)
        assert "**Performance Summary:**" in output
        assert "**Next Week Plan:**" in output
        assert "**Deep Dive:**" in output

    def test_blocks_separated_by_exactly_one_blank_line(self):
        results = [
            {"intent": "performance_summary", "label": "Performance Summary", "response": "A"},
            {"intent": "next_week_plan", "label": "Next Week Plan", "response": "B"},
        ]
        output = assemble(results)
        # Exactly one blank line between blocks — not two
        assert "\n\n\n" not in output
        assert "\n\n" in output

    def test_response_text_preserved_exactly(self):
        long_response = "Line one.\nLine two.\nLine three."
        results = [{"intent": "performance_summary", "label": "Performance Summary", "response": long_response}]
        output = assemble(results)
        assert long_response in output


class TestAssembleEmptyInput:
    def test_empty_list_returns_empty_string(self):
        assert assemble([]) == ""

    def test_empty_list_returns_string_type(self):
        result = assemble([])
        assert isinstance(result, str)
