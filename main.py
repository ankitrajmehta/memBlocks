"""
Interactive CLI for memBlocks - Memory Management System
========================================================

Main entry point for testing the modular memory system.
Provides interactive menu for:
- User management
- Block creation and management
- Chat sessions with memory augmentation
"""

import asyncio
import sys
from typing import Optional

from services.user_service import user_service
from services.block_service import block_service, session_manager
from services.chat_service import ChatService
from models.container import MemoryBlock


class MemBlocksCLI:
    """Interactive CLI for memBlocks system."""
    
    def __init__(self):
        self.current_user_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        self.chat_service: Optional[ChatService] = None
    
    async def initialize(self):
        """Initialize CLI and ensure default test user exists."""
        print("\n" + "="*70)
        print("🧠 MemBlocks - Modular Memory Management System")
        print("="*70)
        
        # Create or get default test user
        default_user = "test_user"
        user = await user_service.get_or_create_user(default_user)
        self.current_user_id = user["user_id"]
        
        print(f"\n✅ Initialized with user: {self.current_user_id}")
    
    def display_status(self):
        """Display current session status."""
        print(f"\n{'─'*70}")
        print(f"📊 Current Status:")
        print(f"   👤 User: {self.current_user_id or 'None'}")
        
        if self.current_session_id:
            session_info = session_manager.get_session(self.current_session_id)
            attached_block_id = session_info.get("attached_block_id") if session_info else None
            print(f"   💬 Session: {self.current_session_id}")
            print(f"   📦 Attached Block: {attached_block_id or 'None'}")
            
            if self.chat_service:
                print(f"   💭 Messages: {len(self.chat_service.message_history)}")
                print(f"   📝 Summary: {'Yes' if self.chat_service.recursive_summary else 'No'}")
        else:
            print(f"   💬 Session: None (no active chat)")
        
        print(f"{'─'*70}\n")
    
    def display_menu(self):
        """Display main menu."""
        print("\n" + "="*70)
        print("MENU:")
        print("="*70)
        print("1. 👤 Select/Create User")
        print("2. 📦 Create Memory Block")
        print("3. 📋 List My Blocks")
        print("4. 🔗 Start Chat Session (Attach Block)")
        print("5. 💬 Chat")
        print("6. 📊 View Status")
        print("7. 🚪 Exit")
        print("="*70)
    
    async def ainput(self, prompt: str = "") -> str:
        """Non-blocking input using asyncio.to_thread. 
            #TODO make needed processes BG thread, and remove this function"""
        return await asyncio.to_thread(input, prompt)

    async def select_create_user(self):
        """Select or create a user."""
        print("\n" + "─"*70)
        print("👤 USER SELECTION")
        print("─"*70)
        
        # List existing users
        users = await user_service.list_users()
        if users:
            print("\nExisting users:")
            for i, user in enumerate(users, 1):
                print(f"  {i}. {user['user_id']}")
        
        choice = (await self.ainput("\nEnter user ID (or press Enter for current): ")).strip()
        
        if not choice:
            print(f"✅ Keeping current user: {self.current_user_id}")
            return
        
        # Get or create user
        user = await user_service.get_or_create_user(choice)
        self.current_user_id = user["user_id"]
        print(f"✅ Selected user: {self.current_user_id}")
    
    async def create_block(self):
        """Create a new memory block."""
        if not self.current_user_id:
            print("⚠️ Please select a user first!")
            return
        
        print("\n" + "─"*70)
        print("📦 CREATE MEMORY BLOCK")
        print("─"*70)
        
        name = (await self.ainput("Block name: ")).strip()
        if not name:
            print("⚠️ Block name is required!")
            return
        
        description = (await self.ainput("Block description: ")).strip()
        if not description:
            description = f"Memory block for {name}"
        
        print("\nCreating block...")
        block = await block_service.create_block(
            user_id=self.current_user_id,
            name=name,
            description=description,
            create_semantic=True,
            create_core=True,
            create_resource=False
        )
        
        print(f"\n✅ Block created successfully!")
        print(f"   ID: {block.meta_data.id}")
        print(f"   Name: {block.name}")
    
    async def list_blocks(self):
        """List user's blocks."""
        if not self.current_user_id:
            print("⚠️ Please select a user first!")
            return
        
        print("\n" + "─"*70)
        print(f"📋 BLOCKS FOR USER: {self.current_user_id}")
        print("─"*70)
        
        blocks = await block_service.list_user_blocks(self.current_user_id)
        
        if not blocks:
            print("\n📭 No blocks found. Create one first!")
            return
        
        for i, block in enumerate(blocks, 1):
            print(f"\n{i}. {block.name}")
            print(f"   ID: {block.meta_data.id}")
            print(f"   Description: {block.description}")
            print(f"   Created: {block.meta_data.created_at}")
            print(f"   Sections: ", end="")
            sections = []
            if block.semantic_memories:
                sections.append("Semantic")
            if block.core_memories:
                sections.append("Core")
            if block.resource_memories:
                sections.append("Resource")
            print(", ".join(sections))
    
    async def start_chat_session(self):
        """Start a chat session with a block attached."""
        if not self.current_user_id:
            print("⚠️ Please select a user first!")
            return
        
        print("\n" + "─"*70)
        print("🔗 START CHAT SESSION")
        print("─"*70)
        
        # List blocks
        blocks = await block_service.list_user_blocks(self.current_user_id)
        
        if not blocks:
            print("\n📭 No blocks found. Create one first!")
            return
        
        print("\nAvailable blocks:")
        for i, block in enumerate(blocks, 1):
            print(f"  {i}. {block.name} ({block.meta_data.id})")
        
        choice = (await self.ainput("\nSelect block number: ")).strip()
        
        try:
            block_idx = int(choice) - 1
            if block_idx < 0 or block_idx >= len(blocks):
                print("⚠️ Invalid selection!")
                return
            
            selected_block = blocks[block_idx]
            
            # Create session
            self.current_session_id = session_manager.create_session(self.current_user_id)
            session_manager.attach_block(self.current_session_id, selected_block.meta_data.id)
            
            # Initialize chat service
            self.chat_service = ChatService(
                memory_block=selected_block,
                memory_window=10,
                keep_last_n=4
            )
            
            print(f"\n✅ Chat session started!")
            print(f"   Session ID: {self.current_session_id}")
            print(f"   Attached Block: {selected_block.name}")
            
        except ValueError:
            print("⚠️ Invalid input!")
    
    async def chat(self):
        """Chat interface."""
        if not self.chat_service:
            print("⚠️ No active chat session! Start a session first (option 4).")
            return
        
        print("\n" + "─"*70)
        print("💬 CHAT MODE")
        print("─"*70)
        print("Type 'exit' to return to menu")
        print("Type 'status' to view session info")
        print("─"*70)
        
        while True:
            user_input = (await self.ainput("\n🙋 You: ")).strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("\n✅ Exiting chat mode...")
                break
            
            if user_input.lower() == 'status':
                self.chat_service.print_status()
                continue
            
            # Send message and get response
            try:
                response = await self.chat_service.send_message(user_input)
                print(f"\n🤖 Assistant: {response}")
            except Exception as e:
                print(f"\n⚠️ Error: {e}")
    
    def view_status(self):
        """View detailed status."""
        self.display_status()
        
        if self.chat_service:
            self.chat_service.print_status()
    
    async def run(self):
        """Main CLI loop."""
        await self.initialize()
        
        while True:
            self.display_status()
            self.display_menu()
            
            choice = (await self.ainput("Select option: ")).strip()
            
            try:
                if choice == '1':
                    await self.select_create_user()
                elif choice == '2':
                    await self.create_block()
                elif choice == '3':
                    await self.list_blocks()
                elif choice == '4':
                    await self.start_chat_session()
                elif choice == '5':
                    await self.chat()
                elif choice == '6':
                    self.view_status()
                elif choice == '7':
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("⚠️ Invalid option!")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n⚠️ Error: {e}")
                import traceback
                traceback.print_exc()


async def main():
    """Entry point."""
    cli = MemBlocksCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
