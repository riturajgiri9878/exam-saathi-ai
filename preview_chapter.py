"""Create an explicitly hand-authored layout preview; no live AI result claimed."""
from pathlib import Path
from chapter_teacher import source_units,source_signature,validate_batch
from study_export import build_study_html

def create_preview(source_path,output_path):
    source=Path(source_path).read_text(encoding='utf-8')
    start=source.index('1.5 Types of tests:')
    end=source.index('1.6 Approach to Evaluation:',start)
    analysis={'documents':[{'source_name':'Pasted_Notes.txt — section 1.5 excerpt',
        'page_number':1,'extraction_method':'Pasted Text','text':source[start:end]}],
        'batch_warnings':['LAYOUT PREVIEW: Hand-authored sample of section 1.5 only. This is not a live Gemini response or a complete guide to the uploaded chapter.'],
        'study_language':'Hinglish'}
    units=source_units(analysis); ids=[u['id'] for u in units]
    topics=[{
        'title':'🧑‍🏫 Teacher-made test — apni class ke learning goals ke liye',
        'definition':'Teacher-made test teacher khud banata hai, apni class mein padhaye gaye content aur learning objectives ko check karne ke liye. Iska focus hota hai: mere students ne kya seekha, kahan difficulty hai aur ab teaching mein kya badalna chahiye?',
        'story':'Socho Meera ma’am ne fractions padhaye. Class mein kuch bachche 1/2 + 1/3 ko 2/5 likh rahe hain. Ma’am agle din ek chhota test banati hain: pehle equivalent fractions, phir common denominator aur aakhir mein ek word problem. Woh sirf total marks nahi dekhti; galat answers ka pattern bhi dekhti hain. Ab unhe pata chalta hai ki bachchon ko addition se pehle equivalent fractions ka concept dobara samjhana hai. Yeh classroom ki need ke hisaab se banaya gaya teacher-made test hai.',
        'steps':[
            'Goal pehle: teacher tay karta hai ki kaunsi knowledge ya skill check karni hai. Sirf chapter ka naam likhna clear objective nahi hai.',
            'Questions goal ke hisaab se: MCQ, short answer, essay, true/false, fill-in-the-blanks ya matching use ho sakte hain. Format purpose se decide hota hai.',
            'Learning ke beech test ho aur feedback se teaching sudhare, toh formative use hai. Unit/term ke end par achievement judge kare, toh summative use hai.',
            'Flexibility iska fayda hai: teacher class ki difficulty dekhkar questions aur feedback jaldi adapt kar sakta hai.',
            'Quality automatic nahi: clear wording, balanced content coverage aur fair scoring ke bina result biased ya inaccurate ho sakta hai.',
            'Blueprint batata hai kis topic/objective se kitne questions honge. Rubric batata hai answer ko marks kis basis par milenge. Dono ka kaam alag hai.'
        ],
        'example':'Illustrative example: ma’am five questions deti hain—two equivalent fractions, two additions aur one word problem. Riya addition wale answers galat karti hai. Ma’am pehle common denominator ka worked example karati hain, phir ek naya question deti hain. Test ka result learning ko improve karne mein use hua; isliye yahan formative purpose hai.',
        'analogy_limit':'Class ki need par focus karna har individual student ke liye alag paper banana zaroori nahi banata. Teacher-made ka matlab easy test bhi nahi hai; difficulty learning objectives ke hisaab se honi chahiye.',
        'memory_tip':'Teacher-made = class goals + teacher design. Blueprint = coverage; rubric = scoring.',
        'takeaways':['Teacher-made tests formative aur summative dono ho sakte hain.','Flexibility aur quick feedback strengths hain.','Reliability/validity teacher ki test-construction skill se affect hoti hain.'],
        'check_question':'Agar Meera ma’am wahi test unit ke end mein final achievement judge karne ke liye use karein, purpose kya hoga? Apna reason bhi do.',
        'source_ids':ids,
        'diagram':{'kind':'sequence','caption':'Illustrative test-design workflow',
            'nodes':[{'label':'🎯 Objective','detail':'Kya learning check karni hai?'},
                     {'label':'🗂️ Blueprint','detail':'Topics aur objectives ko balanced jagah do.'},
                     {'label':'✍️ Questions + rubric','detail':'Clear tasks aur fair marking rules banao.'},
                     {'label':'🔁 Use the evidence','detail':'Feedback do ya achievement judge karo.'}]},
        'comparison':[]
    },{
        'title':'📏 Standardized test — consistent procedures, wider comparison',
        'definition':'Standardized test experts/professional organizations develop karte hain. Ismein administration, instructions, scoring aur interpretation ke consistent procedures hote hain, taaki results ko wider groups mein meaningful tareeke se use kiya ja sake.',
        'story':'Ab socho ek education team ko kai schools ke students ki performance compare karni hai. Agar har school apna alag paper, alag instructions aur alag marking rules use kare, toh scores ka comparison mushkil ho jayega. Team ek planned assessment aur consistent procedures banati hai. Yeh standardized approach ko samajhne ki analogy hai. Lekin ek score student ki creativity, practical skill aur poori personality ka complete picture nahi hota; result ko uske purpose aur limitations ke saath interpret karna padta hai.',
        'steps':[
            'Who designs it? Usually testing experts ya professional organizations, sirf ek classroom ke immediate needs ke liye nahi.',
            'What is standardized? Instructions, administration, scoring aur interpretation ke procedures. Sirf multiple-choice format hona standardization nahi hai.',
            'Why useful? Consistent procedures personal scoring bias ko reduce karne aur groups ke comparisons ko support karne mein madad karte hain.',
            'Result ka reference alag ho sakta hai: norm-referenced mein group se comparison; criterion-referenced mein fixed learning standards se comparison.',
            'Limitations yaad rakho: creativity/practical skills poori tarah capture nahi ho sakti; overemphasis se stress aur teaching-to-the-test badh sakta hai.',
            'Teacher-made aur standardized ko good versus bad mat banao. Selection purpose, required evidence aur context par depend karta hai.'
        ],
        'example':'Illustrative example: ek assessment mein Asha ka result classmates ke scores ke comparison mein interpret hota hai—yeh norm-referenced interpretation hai. Dusre mein check hota hai ki Asha ne fixed skill standard meet kiya ya nahi—yeh criterion-referenced interpretation hai. Standardized hona aur norm-referenced hona ek hi baat nahi hai.',
        'analogy_limit':'Consistent testing procedures ka matlab yeh nahi ki har learner ki zaroorat ignore ki jaye. Analogy accommodations ke complete rules explain nahi karti. Standardization bhi har possible bias ko automatically khatam nahi karti.',
        'memory_tip':'Standardized = consistent procedures. Norm = group; criterion = standard.',
        'takeaways':['Development aur administration teacher-made tests se differ karte hain.','Standardized tests norm- ya criterion-referenced ho sakte hain.','Broader comparison useful hai, lekin score ko complete learner profile na samjho.'],
        'check_question':'Kya har standardized test students ko rank hi karta hai? Norm aur criterion ka difference use karke explain karo.',
        'source_ids':ids,
        'diagram':{'kind':'comparison','caption':'Different questions that test results can answer',
            'nodes':[{'label':'👥 Norm reference','detail':'Group ke comparison mein performance kaisi hai?'},
                     {'label':'🎯 Criterion reference','detail':'Specified skill/standard achieve hua ya nahi?'}]},
        'comparison':[{'term':'Teacher-made','meaning':'Specific classroom goals ke liye teacher design; flexible.','example':'Fractions ki current difficulty check karna.'},
                      {'term':'Standardized','meaning':'Consistent administration/scoring; often wider use.','example':'Schools/groups ki performance compare karna.'}]
    }]
    short=[
        ('Teacher-made test define karo aur ek advantage batao.',
         'Teacher-made test teacher ke dwara classroom objectives aur padhaye gaye content ko assess karne ke liye banaya jata hai. Ek advantage flexibility hai: teacher current learning difficulties ke hisaab se test aur feedback adapt kar sakta hai.',
         'Definition aur flexibility dono source ke central points hain.'),
        ('Blueprint aur scoring rubric mein kya difference hai?',
         'Blueprint test ke content aur objectives ki planned coverage batata hai. Scoring rubric answer/performance ko marks dene ke criteria batata hai. Balanced paper aur fair marking related hain, lekin ek hi task nahi hain.',
         'Test quality improve karne ke do methods ko separate karta hai.'),
        ('Kya teacher-made test sirf formative hota hai?',
         'Nahi. Learning ke dauran feedback ke liye formative use ho sakta hai. Unit/term ke end mein overall achievement judge karne ke liye summative use ho sakta hai. Purpose decide karta hai; creator alone decide nahi karta.',
         'Common misconception ko correct karta hai.')]
    longs=[
        ('Teacher-made aur standardized tests compare karo: design, purpose, advantages aur limitations ke saath.',
         'Teacher-made test teacher apni class ke taught objectives aur content ke liye develop karta hai. Isse quick feedback aur flexible adaptation mil sakta hai. Example: fractions ki difficulty ko identify karne wala class test. Lekin quality clear objectives, balanced coverage aur fair scoring par depend karti hai.\n\nStandardized test experts consistent administration, scoring aur interpretation procedures ke saath develop karte hain. Iska use wider comparisons aur educational decisions mein ho sakta hai. Consistency personal bias reduce karne mein help karti hai, lekin test har practical skill, creativity ya individual difference ka complete measure nahi hota. Overemphasis stress aur narrow teaching ko badha sakta hai.\n\nConclusion: dono ko purpose ke according choose karna chahiye. Teacher-made ko automatically weak aur standardized ko automatically perfect kehna sahi nahi hoga.',
         ['Dono ki definitions likho.','Creator, classroom fit aur procedures compare karo.','Har type ke fayde aur limitations explain karo.','Ek classroom example do aur purpose-based conclusion likho.'],
         'Yeh question section ke definitions, comparison aur critical discussion ko ek saath revise karata hai.'),
        ('Ek teacher-made test ko effective banane ke steps explain karo, example ke saath.',
         'Sabse pehle learning objectives clearly define karo. Fractions unit mein objective sirf “fractions” nahi, balki unlike denominators wale fractions add kar pana ho sakta hai. Phir blueprint/table of specifications se content aur objectives ki coverage plan karo.\n\nQuestions objective ke suitable format mein likho: short problems, explanation questions ya MCQs. Clear wording use karo, taaki language confusion unintended difficulty na ban jaye. Scoring rubric se pehle decide karo ki correct method, working aur final answer ko marks kaise milenge.\n\nResponses ko intended purpose ke liye use karo. Formative use mein repeated errors dekhkar feedback aur remedial teaching do. Summative use mein unit achievement judge karo. Yeh practices test ki effectiveness improve karne ke source-supported principles hain; inhe follow karna perfect validity ki guarantee nahi hai.',
         ['Clear objectives.','Balanced blueprint.','Appropriate question format and wording.','Fair scoring rubric.','Purpose ke according interpretation and feedback.'],
         'Definition ko practical test-construction task mein apply karta hai.')]
    data={'covered_source_ids':ids,'topics':topics,
        'short_questions':[dict(question=q,answer=a,why=w,source_ids=ids) for q,a,w in short],
        'long_questions':[dict(question=q,answer=a,outline=o,why=w,source_ids=ids) for q,a,o,w in longs],
        'revision_points':['Teacher-made: class-specific goals, flexible design.','Standardized: consistent procedures, often wider comparison.','Blueprint plans coverage; rubric plans scoring.','Formative/summative describe purpose; norm/criterion describe reference.']}
    validate_batch(data,units)
    lesson={'source_signature':source_signature(analysis),'language':'Hinglish','units':units,
        'batches':{'0':data},'status':'complete','total_batches':1,
        'source_warnings':analysis['batch_warnings'],'skipped_pages':0}
    output=build_study_html(dict(analysis,detailed_lesson=lesson),
        'Teacher-made & Standardized Tests — Layout Preview')
    output=output.replace('<main>','<main><p class="warning"><strong>Hand-authored layout preview — section 1.5 only.</strong> Not a live Gemini result. The application builds lessons from your own processed notes.</p>',1)
    Path(output_path).write_text(output,encoding='utf-8')

if __name__=='__main__':
    import sys
    create_preview(sys.argv[1],sys.argv[2])
