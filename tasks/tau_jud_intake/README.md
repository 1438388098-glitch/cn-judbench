# tau_jud_intake

τ-Jud 执业接待（L3b，impl-P3 §2）。

- **模拟用户**：`user_scripts/us-intake-01.yaml`（personas + sampling + 禁泄 gold）。
- **主分**：终态 F1（`state_goal`）× Proto 红线 gate；`pass^k` 固定/换 persona 双列。
- **run**：`python -m cnjudbench run-dialog --task tau_jud_intake --model mock:dialog --user-seed 42 --k-pass 3`
- **方差**：model / user_script / judge 分列，禁止把用户噪声记在模型账上。
