"""
Typeclass Application Constants
รวมค่าคงที่และชุดข้อมูลคำศัพท์สำหรับระบบฝึกพิมพ์ดีด
"""

# ชุดคำศัพท์ทั่วไปสำหรับการฝึกพิมพ์
GENERAL_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "it", "is", "on", "as", "do", "at", "go", "no", "up", "if", "me",
    "that", "have", "this", "from", "they", "will", "what", "time", "just", "like", "know", "take", "year", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "important", "something", "different", "experience", "information", "everything", "understand", "sometimes", "development", "environment", "government", "education", "especially", "completely", "themselves", "possibility", "technology", "comfortable", "interesting"
]

# ชุดคำศัพท์เฉพาะทางด้านการเขียนโปรแกรม (Coding keywords)
CODING_WORDS = [
    "python", "def", "init", "self", "return", "print", "import", "from", "class", 
    "pass", "try", "except", "True", "False", "None", "elif", "else", "for", "while", 
    "break", "continue", "lambda", "yield", "with", "async", "await", 
    "str", "int", "float", "list", "dict", "set", "tuple", "map", "filter", "len", "range", "open"
]

# เกณฑ์ความเร็วสูงสุดที่อนุญาต (WPM) ก่อนถูกระบบ Anti-Cheat ตั้งสถานะ Flagged
# (เกณฑ์สถิติโลกมนุษย์สูงสุดประมาณ 212-216 WPM ดังนั้น 240 WPM ถือเป็นเพดานสูงสุดที่มนุษย์ทำได้)
MAX_WPM_THRESHOLD = 240
