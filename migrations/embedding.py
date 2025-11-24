"""
Script to generate embeddings for tour packages
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.v1.core.config import settings
from app.v1.core.supabase import supabase_client
from openai import AsyncOpenAI
import numpy as np
from typing import List, Dict, Any


class TourEmbeddingGenerator:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.supabase = supabase_client
    
    async def get_tour_packages(self) -> List[Dict[str, Any]]:
        """Get all active tour packages from database"""
        try:
            result = self.supabase.table("tour_packages").select("*").eq("is_active", True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching tour packages: {e}")
            return []
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return []
    
    def create_embedding_text(self, package: Dict[str, Any]) -> str:
        """Create comprehensive text for embedding from tour package"""đ
        # Combine all relevant information
        text_parts = [
            f"Tour: {package.get('package_name', '')}",
            f"Destination: {package.get('destination', '')}",
            f"Description: {package.get('description', '')}",
            f"Duration: {package.get('duration_days', 0)} days",
            f"Price: {package.get('price', 0)} VND",
            f"Departure: {package.get('departure_location', '')}",
            f"Available slots: {package.get('available_slots', 0)}",
        ]
        
        # Add includes
        if package.get('includes'):
            includes_text = ", ".join(package['includes']) if isinstance(package['includes'], list) else str(package['includes'])
            text_parts.append(f"Includes: {includes_text}")
        
        # Add excludes
        if package.get('excludes'):
            excludes_text = ", ".join(package['excludes']) if isinstance(package['excludes'], list) else str(package['excludes'])
            text_parts.append(f"Excludes: {excludes_text}")
        
        # Add itinerary if available
        if package.get('itinerary'):
            itinerary_text = str(package['itinerary'])
            text_parts.append(f"Itinerary: {itinerary_text}")
        
        return " | ".join(text_parts)
    
    async def process_package(self, package: Dict[str, Any]) -> bool:
        """Process single package and store embedding"""
        try:
            package_id = package['package_id']
            
            # Check if embedding already exists
            existing = self.supabase.table("package_embeddings").select("package_id").eq("package_id", package_id).execute()
            if existing.data:
                print(f"⏭️  Embedding already exists for {package['package_name']}")
                return True
            
            # Create embedding text
            embedding_text = self.create_embedding_text(package)
            print(f"📝 Processing: {package['package_name']}")
            
            # Generate embedding
            embedding = await self.generate_embedding(embedding_text)
            if not embedding:
                print(f"❌ Failed to generate embedding for {package['package_name']}")
                return False
            
            # Store embedding
            embedding_data = {
                "package_id": package_id,
                "embedding": embedding
            }
            
            result = self.supabase.table("package_embeddings").insert(embedding_data).execute()
            if result.data:
                print(f"✅ Stored embedding for {package['package_name']}")
                return True
            else:
                print(f"❌ Failed to store embedding for {package['package_name']}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing package {package.get('package_name', 'Unknown')}: {e}")
            return False
    
    async def generate_all_embeddings(self):
        """Generate embeddings for all tour packages"""
        print("🚀 Starting Tour Package Embedding Generation")
        print("=" * 60)
        
        # Get all tour packages
        packages = await self.get_tour_packages()
        if not packages:
            print("❌ No tour packages found")
            return
        
        print(f"📊 Found {len(packages)} tour packages")
        
        # Process each package
        success_count = 0
        for i, package in enumerate(packages, 1):
            print(f"\n[{i}/{len(packages)}] Processing package...")
            success = await self.process_package(package)
            if success:
                success_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("📊 EMBEDDING GENERATION RESULTS")
        print("=" * 60)
        print(f"✅ Successfully processed: {success_count}/{len(packages)}")
        print(f"❌ Failed: {len(packages) - success_count}/{len(packages)}")
        
        if success_count == len(packages):
            print("\n🎉 All embeddings generated successfully!")
        else:
            print(f"\n⚠️  {len(packages) - success_count} packages failed. Check logs above.")
    
    async def test_embedding_search(self, query: str = "tour Đà Lạt 3 ngày"):
        """Test embedding-based search"""
        print(f"\n🔍 Testing embedding search for: '{query}'")
        
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            if not query_embedding:
                print("❌ Failed to generate query embedding")
                return
            
            # Get all embeddings and calculate similarity manually
            all_embeddings = self.supabase.table("package_embeddings").select("package_id, embedding").execute()
            
            if not all_embeddings.data:
                print("❌ No embeddings found in database")
                return
            
            # Calculate similarities manually
            import numpy as np
            results = []
            for emb_data in all_embeddings.data:
                pkg_id = emb_data['package_id']
                pkg_emb_raw = emb_data['embedding']
                
                # Parse embedding string to array
                if isinstance(pkg_emb_raw, str):
                    # Remove brackets and split
                    pkg_emb = [float(x) for x in pkg_emb_raw.strip('[]').split(',')]
                else:
                    pkg_emb = pkg_emb_raw
                
                # Convert to numpy arrays
                query_vec = np.array(query_embedding)
                pkg_vec = np.array(pkg_emb)
                
                # Calculate cosine similarity
                similarity = np.dot(query_vec, pkg_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(pkg_vec)
                )
                
                if similarity > 0.3:
                    # Get package details
                    pkg = self.supabase.table("tour_packages").select("*").eq("package_id", pkg_id).single().execute()
                    if pkg.data:
                        results.append({
                            **pkg.data,
                            'similarity': similarity
                        })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            results = results[:5]
            
            if results:
                print(f"✅ Found {len(results)} similar packages:")
                for i, match in enumerate(results, 1):
                    print(f"  {i}. {match.get('package_name', 'Unknown')}")
                    print(f"     Destination: {match.get('destination', 'Unknown')}")
                    print(f"     Similarity: {match.get('similarity', 0):.3f}")
            else:
                print("❌ No similar packages found (similarity > 0.3)")
                
        except Exception as e:
            print(f"❌ Error testing embedding search: {e}")


async def main():
    """Main function"""
    generator = TourEmbeddingGenerator()
    
    # Generate embeddings
    await generator.generate_all_embeddings()
    
    # Test search
    await generator.test_embedding_search("Trải nghiệm hoàn hảo tại hòn đảo ngọc Phú Quốc - thiên đường biển đảo của Việt Nam với bãi biển nước trong xanh ngọc bích được CNN bình chọn là một trong những bãi biển đẹp nhất thế giới. Tour bao gồm: Khám phá VinWonders Phú Quốc - công viên giải trí lớn nhất Việt Nam với hơn 100 trò chơi cảm giác mạnh và các show diễn đẳng cấp quốc tế, tham quan Vinpearl Safari - vườn thú bán hoang dã đầu tiên tại Việt Nam với hơn 3000 cá thể động vật quý hiếm, trải nghiệm cáp treo 3 dây Hòn Thơm dài nhất thế giới vượt biển ngắm hoàng hôn tuyệt đẹp, lặn ngắm san hô và sinh vật biển tại các đảo nhỏ xung quanh, tắm biển tại Bãi Sao - bãi biển cát trắng mịn như bột, tham quan làng chài Hàm Ninh thưởng thức hải sản tươi sống, khám phá chợ đêm Phú Quốc mua sắm đặc sản như nước mắm, sim rượu, ngọc trai. Phù hợp cho gia đình, cặp đôi, nhóm bạn muốn nghỉ dưỡng và khám phá biển đảo.")
    await generator.test_embedding_search("Nha Trang 4 ngày 3 đêm")
    await generator.test_embedding_search("Phú Quốc resort 5 sao")


if __name__ == "__main__":
    asyncio.run(main())
