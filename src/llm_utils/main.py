#!/usr/bin/env python3
"""
Optimized RFP Analyzer - Main Pipeline
Unified interface for RFP analysis tasks
"""

import os
import sys
from pathlib import Path
from technical_requirements import GetTechnicalRequirement
from document_requirements import GetDocumentRequirement

class RFPAnalyzerPipeline:
    """Main pipeline for RFP analysis operations"""
    
    def __init__(self):
        self.technical_analyzer = GetTechnicalRequirement()
        self.document_analyzer = GetDocumentRequirement()
        
        # Default output directories
        self.base_dir = "/Users/viswanaath.krishnamoorthy/Documents/PRISM_HACKATHON"
        self.rfp_output_dir = os.path.join(self.base_dir, "outputs/Summary")
        self.knowledge_base_dir = os.path.join(self.base_dir, "outputs/Knowledge_base")
        self.document_analysis_dir = os.path.join(self.base_dir, "outputs/Document_Analysis")
        self.document_kb_dir = os.path.join(self.base_dir, "outputs/Document_Knowledge_base")
        
        # Ensure output directories exist
        for directory in [self.rfp_output_dir, self.knowledge_base_dir, 
                         self.document_analysis_dir, self.document_kb_dir]:
            os.makedirs(directory, exist_ok=True)

    def display_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("🔍 OPTIMIZED RFP ANALYZER")
        print("="*60)
        print("\n📋 TECHNICAL REQUIREMENTS ANALYSIS:")
        print("1. Summarize Single RFP (Technical Requirements)")
        print("2. Create Knowledge Base from RFP Folder (Technical)")
        print("\n📄 DOCUMENT REQUIREMENTS ANALYSIS:")
        print("3. Analyze Document Requirements (Single RFP)")
        print("4. Create Document Knowledge Base (RFP Folder)")
        print("\n🔧 UTILITIES:")
        print("5. Compare RFPs (Coming Soon)")
        print("6. Batch Process Multiple RFPs (Coming Soon)")
        print("\n0. Exit")
        print("="*60)

    def get_file_path(self, prompt: str, must_exist: bool = True) -> str:
        """Get and validate file path from user"""
        while True:
            path = input(f"\n{prompt}: ").strip()
            if not path:
                print("❌ Please enter a valid path.")
                continue
            
            if must_exist and not os.path.exists(path):
                print(f"❌ Path does not exist: {path}")
                continue
            
            return path

    # def get_output_path(self, default_dir: str, source_path: str, suffix: str) -> str:
    #     """Generate output path with user confirmation"""
    #     filename = os.path.basename(source_path)
    #     if filename.endswith('.pdf'):
    #         filename = filename.replace('.pdf', suffix)
    #     else:
    #         filename = filename + suffix
        
    #     default_output = os.path.join(default_dir, filename)
        
    #     print(f"\n📁 Default output path: {default_output}")
    #     custom_path = input("Enter custom output path (or press Enter for default): ").strip()
        
    #     return custom_path if custom_path else default_output

    def summarize_single_rfp(self, rfp_path):
        """Option 1: Summarize single RFP for technical requirements"""
        print("\n🔍 SUMMARIZE SINGLE RFP (Technical Requirements)")
        print("-" * 50)
        filename = rfp_path.split('/')[-1].replace('.pdf','.txt')
        
        output_path = os.path.join(self.rfp_output_dir, filename)
        
        print(f"\n🚀 Processing: {os.path.basename(rfp_path)}")
        success = self.technical_analyzer.summarize_rfp(rfp_path, output_path)
        
        if success:
            print(f"✅ Summary completed successfully!")
            print(f"📄 Output saved to: {output_path}")
        else:
            print("❌ Failed to generate summary.")

    def create_technical_knowledge_base(self, folder_path):
        """Option 2: Create knowledge base from RFP folder (technical)"""
        print("\n📚 CREATE TECHNICAL KNOWLEDGE BASE")
        print("-" * 50)
        
        # folder_path = self.get_file_path("Enter RFP folder path")
        # if not os.path.isdir(folder_path):
        #     print("❌ Please provide a valid directory path.")
        #     return
        filename = folder_path.split('/')[-1]
        output_path = os.path.join(self.knowledge_base_dir, f"{filename}__Knowledge_Base.txt")
        
        print(f"\n🚀 Processing folder: {os.path.basename(folder_path)}")
        success = self.technical_analyzer.create_knowledge_base(folder_path, output_path)
        
        if success:
            print(f"✅ Knowledge base created successfully!")
            print(f"📄 Output saved to: {output_path}")
        else:
            print("❌ Failed to create knowledge base.")

    def analyze_document_requirements(self, rfp_path):
        """Option 3: Analyze document requirements in single RFP"""
        print("\n📋 ANALYZE DOCUMENT REQUIREMENTS")
        print("-" * 50)
        
        filename = rfp_path.split('/')[-1].replace('.pdf','.txt')
        
        output_path = os.path.join(self.document_analysis_dir, filename)
        
        print(f"\n🚀 Processing: {os.path.basename(rfp_path)}")
        success = self.document_analyzer.analyze_document_requirements(rfp_path, output_path)
        
        if success:
            print(f"✅ Document analysis completed successfully!")
            print(f"📄 Output saved to: {output_path}")
        else:
            print("❌ Failed to analyze document requirements.")

    def create_document_knowledge_base(self, folder_path):
        """Option 4: Create document knowledge base from RFP folder"""
        print("\n📚 CREATE DOCUMENT KNOWLEDGE BASE")
        print("-" * 50)
        
        filename = folder_path.split('/')[-1]
        output_path = os.path.join(self.document_kb_dir, f"{filename}__Knowledge_Base.txt")
        
        print(f"\n🚀 Processing folder: {os.path.basename(folder_path)}")
        success = self.document_analyzer.create_document_knowledge_base(folder_path, output_path)
        
        if success:
            print(f"✅ Document knowledge base created successfully!")
            print(f"📄 Output saved to: {output_path}")
        else:
            print("❌ Failed to create document knowledge base.")

    def execute_choice(self, choice: str, filepath: str, folder_path: str):
        """Execute a specific choice"""
        if choice == '1':
            self.summarize_single_rfp(filepath)
        elif choice == '2':
            self.create_technical_knowledge_base(folder_path)
        elif choice == '3':
            self.analyze_document_requirements(filepath)
        elif choice == '4':
            self.create_document_knowledge_base(folder_path)
        elif choice in ['5', '6']:
            print("\n🚧 This feature is coming soon!")
        else:
            print(f"\n❌ Invalid option: {choice}. Please select 1-6.")
            return False
        return True

    def run(self, choice=None, filepath='', folder_path=''):
        """Main execution loop - supports both interactive and programmatic usage
        
        Args:
            choice (str, optional): If provided, executes this choice directly.
                                  If None, runs interactive menu loop.
        """
        if choice is not None:
            # Programmatic usage - execute specific choice
            print("🚀 RFP Analyzer - Programmatic Mode")
            try:
                return self.execute_choice(str(choice), filepath, folder_path)
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                return False
        
        

def main():
    """Entry point"""
    pipeline = RFPAnalyzerPipeline()
    filepath = '/Users/viswanaath.krishnamoorthy/Documents/PRISM_HACKATHON/NEW_RFP/FinTech Onboarding RFE FOR AI ML DRIVEN DOCUMENT VETTING_SV_21072025.pdf'
    # summarize_rfp(rfp_path, output_path)
    # 1 summarize_single_rfp
    # 2 create_technical_knowledge_base
    # 3 analyze_document_requirements
    # 4 create_document_knowledge_base

    folder_path = '/Users/viswanaath.krishnamoorthy/Documents/PRISM_HACKATHON/RFP_documents/Past_RFP/Hinduja RFP'
    
    pipeline.run(choice='4', filepath=filepath, folder_path=folder_path)

if __name__ == "__main__":
    main()
