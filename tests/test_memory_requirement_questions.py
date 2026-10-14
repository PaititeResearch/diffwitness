import unittest

import test_continuity_questions as fixtures
from diffwitness.continuity_questions import answer_question


class RequirementQuestionTests(unittest.TestCase):
    setUp = fixtures.MemoryQuestionTests.setUp
    record = fixtures.MemoryQuestionTests.record
    assert_sources = fixtures.MemoryQuestionTests.assert_sources

    def test_human_requirement_question_cites_exact_reason(self):
        source = self.record('DEC-HUMAN-RULES-20261014',
            'Keep the three numeric rules in rules.py independent.',
            payload={'why': 'Owner requirement; runtime verification is separate.'})
        before = self.paths.events.read_bytes()
        for modal in ('must', 'should'):
            for verb in ('remain', 'stay'):
                result = answer_question(self.repo,
                    f'Why {modal} the three numeric rules in rules.py {verb} independent?')
                self.assertEqual(result['status'], 'cited-records')
                self.assertEqual(len(result['parts']), 1)
                self.assertEqual(result['parts'][0]['source']['eventId'], source['event_id'])
                self.assertEqual(result['context']['facts'][0]['epistemicStatus'], 'DECLARED')
                self.assert_sources(result)
        self.assertEqual(before, self.paths.events.read_bytes())
        self.assertFalse(self.paths.state.exists())

    def test_requirement_matching_retains_qualifiers_negation_and_order(self):
        self.record('DEC', 'Keep the numeric rules independent.', payload={'why': 'Owner requirement'})
        for question in (
            'Why must the numeric rules remain independent for billing?',
            'Why must the numeric rules remain not independent?',
            'Why must the numeric rules not remain independent?',
            'Why must independent rules remain numeric?',
            'Why must the numeric rules remain independent and why billing?',
            'Why must the numeric rules remain independent since yesterday?',
        ):
            for options in ({}, {'entity': 'DEC'}):
                with self.subTest(question=question, options=options):
                    result = answer_question(self.repo, question, **options)
                    self.assertEqual(result['status'], 'abstained')
                    self.assertEqual(result['parts'], [])

    def test_requirement_does_not_match_negated_or_unrelated_label(self):
        for label in ('Do not keep the numeric rules independent.',
                      'Keep the numeric rules not independent.',
                      'Keep independent numeric rules.',
                      'The numeric rules are independent.'):
            self.record('DEC', label, payload={'why': 'Different assertion'})
            result = answer_question(self.repo, 'Why must the numeric rules remain independent?')
            self.assertEqual(result['status'], 'abstained')

    def test_same_directive_keeps_multiple_recorded_reasons(self):
        for identity in ('DEC-A', 'DEC-B'):
            self.record(identity, 'Keep shared state isolated.', payload={'why': identity})
        result = answer_question(self.repo, 'Why should shared state stay isolated?')
        self.assertEqual(result['status'], 'cited-records')
        self.assertEqual(result['context']['coverage']['matches'], 2)
        self.assert_sources(result)

    def test_literal_memory_and_unknown_requirement_forms_are_not_rewritten(self):
        self.record('DEC', 'Keep shared state isolated.', payload={'why': 'Owner requirement'})
        result = answer_question(self.repo, 'Why must shared state remain isolated?', kind='memory')
        self.assertEqual(result['status'], 'abstained')
        self.assertEqual(answer_question(self.repo, 'Why could shared state become isolated?')['status'], 'abstained')


