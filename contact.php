<?php
/**
 * 夢進堂 - お問い合わせフォーム送信処理
 */

// 設定
$to = 'hrkz1981@gmail.com';
$subject_prefix = '【夢進堂ポートフォリオ】';

// POSTリクエスト以外はリダイレクトまたは終了
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.html');
    exit;
}

// 入力データの取得とサニタイズ
$name = isset($_POST['name']) ? htmlspecialchars(trim($_POST['name'])) : '';
$email = isset($_POST['email']) ? filter_var(trim($_POST['email']), FILTER_SANITIZE_EMAIL) : '';
$subject_input = isset($_POST['subject']) ? htmlspecialchars(trim($_POST['subject'])) : 'お問い合わせ';
$message = isset($_POST['message']) ? htmlspecialchars(trim($_POST['message'])) : '';

// バリデーション
if (empty($name) || empty($email) || empty($message) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    echo json_encode(['status' => 'error', 'message' => '入力内容に不備があります。']);
    exit;
}

// メール本文の作成
$full_subject = $subject_prefix . $subject_input;
$email_body = "夢進堂のウェブサイトから新しいお問い合わせがありました。\n\n";
$email_body .= "--------------------------------------------------\n";
$email_body .= "お名前: $name\n";
$email_body .= "メールアドレス: $email\n";
$email_body .= "件名: $subject_input\n";
$email_body .= "内容:\n$message\n";
$email_body .= "--------------------------------------------------\n";

// メールヘッダーの作成
$headers = "From: $email" . "\r\n" .
           "Reply-To: $email" . "\r\n" .
           "X-Mailer: PHP/" . phpversion();

// メール送信の実行
if (mail($to, $full_subject, $email_body, $headers)) {
    echo json_encode(['status' => 'success', 'message' => 'お問い合わせありがとうございます。メッセージは送信されました。']);
} else {
    echo json_encode(['status' => 'error', 'message' => '送信に失敗しました。サーバーの設定をご確認ください。']);
}
?>
