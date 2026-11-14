"""Synthetic Indian student names used by the deterministic seed."""

INDIAN_STUDENT_NAMES = [
    "Aarav Sharma", "Aadhya Reddy", "Vihaan Patel", "Ananya Iyer", "Arjun Nair",
    "Diya Singh", "Aditya Rao", "Ishita Gupta", "Reyansh Mehta", "Meera Menon",
    "Kabir Joshi", "Saanvi Kulkarni", "Rohan Verma", "Avni Desai", "Krishna Pillai",
    "Myra Kapoor", "Siddharth Mishra", "Navya Bhat", "Dhruv Choudhary", "Kiara Shah",
    "Atharv Patil", "Aanya Bose", "Vivaan Malhotra", "Prisha Jain", "Sai Kiran",
    "Nitya Krishnan", "Arnav Saxena", "Tara Banerjee", "Rudra Shetty", "Ira Sinha",
    "Yash Agarwal", "Riya Narayanan", "Dev Khanna", "Mahi Srinivasan", "Neil Dutta",
    "Kavya Hegde", "Shaurya Tiwari", "Anika Naidu", "Om Prakash", "Aarohi Das",
    "Lakshya Yadav", "Tanvi Ghosh", "Harsh Vardhan", "Veda Subramanian", "Aryan Thakur",
    "Siya Mukherjee", "Manav Bansal", "Aditi Kaur", "Ritvik Pandey", "Trisha Gowda",
    "Nirvaan Arora", "Aisha Qureshi", "Varun Ramesh", "Samaira Roy", "Abhinav Dubey",
    "Sneha Thomas", "Karthik Venkatesh", "Amaira Chawla", "Parth Tripathi", "Nandini Babu",
    "Eshan Jha", "Lavanya Suresh", "Vedant Solanki", "Zoya Khan", "Madhav Purohit",
    "Shruti Anand", "Ayaan Mirza", "Pooja Mahajan", "Rishi Nambiar", "Anvi Mathur",
    "Jayant Raut", "Kritika Lal", "Ishaan Goel", "Bhavya Chakraborty", "Raghav Bedi",
    "Srishti Mondal", "Samar Bajaj", "Anushka Parmar", "Akhil Varma", "Charvi Acharya",
    "Roshan Fernandes", "Neha Sawant", "Surya Teja", "Janvi Rawat", "Gautam Ahuja",
    "Preeti Chandra", "Nikhil Kamath", "Roshni George", "Tejas Apte", "Mira Bhattacharya",
    "Vikram Salvi", "Pallavi Sen", "Aman Oberoi", "Keerthi Rajan", "Rahul Chauhan",
    "Sakshi Kohli", "Naveen Reddy", "Deepa Iqbal", "Ajay Soni", "Harini Mohan",
]


def indian_student_name(index: int) -> str:
    """Return a deterministic synthetic name for a zero-based student index."""
    return INDIAN_STUDENT_NAMES[index % len(INDIAN_STUDENT_NAMES)]
