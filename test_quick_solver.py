import unittest
from quick_solver import (solve_question,solver_prompt,verify_numeric_payload,
                          needs_numeric_verification,needs_science_review,
                          review_science_answer)


class QuickSolverTests(unittest.TestCase):
    def test_single_math_question_needs_no_upload(self):
        seen=[]
        def provider(prompt,structured):
            seen.append(prompt)
            self.assertTrue(structured)
            return {'solution_markdown':'### Steps\nThe inner value simplifies to sqrt(6)+sqrt(3).',
                    'verification_expression':'(sqrt(18)/(sqrt(12)-sqrt(6)))**10',
                    'claimed_final_expression':'817209+577854*sqrt(2)'}
        q=r'Find the exact value of (sqrt(18)/(sqrt(12)-sqrt(6)))^10'
        history=solve_question(q,[],"English",provider)
        self.assertEqual(history[0]['role'],'user')
        self.assertEqual(history[1]['role'],'assistant')
        self.assertIn('817209+577854*sqrt(2)',history[1]['content'])
        self.assertIn('preserve exact fractions/radicals',seen[0])
        self.assertIn(q,seen[0])

    def test_exam_saathi_wrong_answer_is_rejected(self):
        bad={'solution_markdown':'steps','verification_expression':'(sqrt(18)/(sqrt(12)-sqrt(6)))**10',
             'claimed_final_expression':'817209+575910*sqrt(2)'}
        with self.assertRaisesRegex(ValueError,'Calculator mismatch'):
            verify_numeric_payload(bad)

    def test_wrong_first_answer_is_repaired_before_display(self):
        replies=[
            {'solution_markdown':'wrong working','verification_expression':'(sqrt(18)/(sqrt(12)-sqrt(6)))**10',
             'claimed_final_expression':'817209+575910*sqrt(2)'},
            {'solution_markdown':'corrected working','verification_expression':'(sqrt(18)/(sqrt(12)-sqrt(6)))**10',
             'claimed_final_expression':'817209+577854*sqrt(2)'}]
        calls=[]
        def provider(prompt,structured):
            calls.append(prompt);return replies[len(calls)-1]
        result=solve_question('Find the exact value of (sqrt(18)/(sqrt(12)-sqrt(6)))^10',[],'English',provider)
        self.assertEqual(len(calls),2)
        self.assertNotIn('575910',result[-1]['content'])
        self.assertIn('577854',result[-1]['content'])

    def test_numeric_detection(self):
        self.assertTrue(needs_numeric_verification('calculate sqrt(18) exactly'))
        self.assertFalse(needs_numeric_verification('Explain photosynthesis'))
        chemistry=('A reversible gaseous reaction 2A(g) <=> B(g)+C(g) is in a closed '
                   'vessel. At constant temperature total pressure changes from 1.0 to '
                   '1.2 atm. Calculate equilibrium pressure and reverse rate constant.')
        self.assertFalse(needs_numeric_verification(chemistry))

    def test_inconsistent_science_problem_can_return_diagnostic_answer(self):
        question=('For 2A(g) <=> B(g)+C(g), a rigid closed vessel starts at 1.0 atm '
                  'and allegedly reaches 1.2 atm at constant temperature. Calculate equilibrium.')
        calls=[]
        def provider(prompt,structured):
            calls.append(structured)
            if structured:
                return {'verdict':'inconsistent','issues':['pressure contradiction'],
                        'final_answer':('The data are inconsistent: delta n_gas = 0. '
                                        'No unique result can be calculated.')}
            return ('The data are inconsistent: delta n_gas = (1+1)-2 = 0, so at '
                    'constant T and V total pressure remains 1.0 atm. No unique partial '
                    'pressures or reverse rate constant can be calculated.')
        answer=solve_question(question,[],'English',provider)[-1]['content']
        self.assertEqual(calls,[False,True])
        self.assertIn('inconsistent',answer)
        self.assertIn('No unique',answer)

    def test_multistep_organic_question_uses_independent_examiner(self):
        question=('An organic compound undergoes reaction and ozonolysis to a compound, '
                  'then intramolecular aldol reaction and Grignard reagent. The product '
                  'gives an iodoform test. Identify every compound and verify the reagent '
                  'sequence and product structure from the molecular formula.')
        self.assertTrue(needs_science_review(question))
        reviewed=review_science_answer(
            question,'A terminal methyl group always gives iodoform.','English',
            lambda prompt,structured: {
                'verdict':'corrected','issues':['named-test rule'],
                'final_answer':'A methyl group alone is insufficient for the iodoform test.'})
        self.assertIn('Corrected by independent science review',reviewed)
        self.assertIn('alone is insufficient',reviewed)

    def test_short_science_definition_avoids_second_call(self):
        self.assertFalse(needs_science_review('What is the iodoform test?'))

    def test_follow_up_context_and_selected_language(self):
        history=[{'role':'user','content':'What is force?'},
                 {'role':'assistant','content':'Force changes motion.'}]
        prompt=solver_prompt('Give an example',history,'Odia')
        self.assertIn('Target language: Odia',prompt)
        self.assertIn('What is force?',prompt)

    def test_empty_and_oversized_questions_rejected(self):
        with self.assertRaisesRegex(ValueError,'Type a question'):
            solve_question('',[],'English',lambda p,s:'answer')
        with self.assertRaisesRegex(ValueError,'4,000'):
            solve_question('x'*4001,[],'English',lambda p,s:'answer')


if __name__=='__main__': unittest.main()
