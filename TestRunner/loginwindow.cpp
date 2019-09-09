#include "loginwindow.hpp"

LoginWindow::LoginWindow(QWidget *parent)
    : QDialog(parent), ui(new Ui::LoginDialog)
{
    ui->setupUi(this);
}

QString LoginWindow::userName() const
{
    return ui->userEdit->text();
}

QString LoginWindow::password() const
{
    return ui->passwordEdit->text();
}

QString LoginWindow::host() const
{
    return ui->serverEdit->text();
}

