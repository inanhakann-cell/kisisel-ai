"""Toplanan geri bildirimlerle modele LoRA ince ayarı yapar (GPU gerekir).

Kurulum:  pip install unsloth trl datasets
Çalıştır: python egit.py --temel unsloth/Qwen2.5-7B-Instruct-bnb-4bit
Sonra üretilen GGUF dosyasını Ollama'ya ekle (README'deki adımlar).
"""
import argparse

from asistan import geri_bildirim


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--temel", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    p.add_argument("--cikti", default="cikti/benim-modelim")
    p.add_argument("--adim", type=int, default=60)
    a = p.parse_args()

    ornekler = geri_bildirim.egitim_ornekleri()
    if len(ornekler) < 20:
        raise SystemExit(f"Sadece {len(ornekler)} örnek var. Eğitim için en az 20 (ideali 200+) gerekli.")

    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(a.temel, max_seq_length=4096, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=16, lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    veri = Dataset.from_list(ornekler).map(
        lambda o: {"text": tokenizer.apply_chat_template(o["messages"], tokenize=False)})
    SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=veri,
               args=SFTConfig(dataset_text_field="text", per_device_train_batch_size=2,
                              gradient_accumulation_steps=4, max_steps=a.adim, learning_rate=2e-4,
                              logging_steps=5, output_dir="cikti/egitim")).train()
    model.save_pretrained_gguf(a.cikti, tokenizer, quantization_method="q4_k_m")
    print(f"Bitti. GGUF modeli: {a.cikti}")


if __name__ == "__main__":
    main()
