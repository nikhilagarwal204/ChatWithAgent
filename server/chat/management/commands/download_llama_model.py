import os
import requests
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Downloads the Llama model if not already present'

    def handle(self, *args, **kwargs):
        model_dir = os.path.join(settings.BASE_DIR, 'models')
        model_path = settings.LLAMA_MODEL_PATH
        
        # Create the models directory if it doesn't exist
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        if os.path.exists(model_path):
            self.stdout.write(self.style.SUCCESS(f'Llama model already exists at {model_path}'))
            return
        
        self.stdout.write('Downloading Llama model...')
        
        # Replace this URL with the actual download URL for your model
        # This is just a placeholder since we can't distribute the actual model URL
        download_url = "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q2_K.gguf"
        
        try:
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(model_path, 'wb') as file, tqdm(
                    desc=model_path,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                for data in response.iter_content(chunk_size=1024):
                    size = file.write(data)
                    bar.update(size)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully downloaded Llama model to {model_path}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error downloading model: {str(e)}'))
            if os.path.exists(model_path):
                os.remove(model_path)