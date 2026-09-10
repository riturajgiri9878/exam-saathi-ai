import unittest
from quick_solver import solve_question,solver_prompt


class QuickSolverTests(unittest.TestCase):
    def test_single_math_question_needs_no_upload(self):
        seen=[]
        def provider(prompt):
            seen.append(prompt)
            return ('### Steps\nThe expression simplifies to sqrt(6)+sqrt(3). '
                    'Its tenth power is 817209 + 577854 sqrt(2).\n\n'
                    '**Final answer:** 817209 + 577854 sqrt(2)')
        q=r'Find the exact value of (sqrt(18)/(sqrt(12)-sqrt(6)))^10'
        history=solve_question(q,[],"English",provider)
        self.assertEqual(history[0]['role'],'user')
        self.assertEqual(history[1]['role'],'assistant')
        self.assertIn('817209',history[1]['content'])
        self.assertIn('preserve exact fractions/radicals',seen[0])
        self.assertIn(q,seen[0])

    def test_follow_up_context_and_selected_language(self):
        history=[{'role':'user','content':'What is force?'},
                 {'role':'assistant','content':'Force changes motion.'}]
        prompt=solver_prompt('Give an example',history,'Odia')
        self.assertIn('Target language: Odia',prompt)
        self.assertIn('What is force?',prompt)

    def test_empty_and_oversized_questions_rejected(self):
        with self.assertRaisesRegex(ValueError,'Type a question'):
            solve_question('',[],'English',lambda p:'answer')
        with self.assertRaisesRegex(ValueError,'4,000'):
            solve_question('x'*4001,[],'English',lambda p:'answer')


if __name__=='__main__': unittest.main()
