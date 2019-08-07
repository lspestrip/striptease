#pragma once

#include <QDialog>
#include "ui_login.h"

class LoginWindow : public QDialog
{
    Q_OBJECT
public:
    explicit LoginWindow(QWidget *parent = nullptr);

    QString userName() const;
    QString password() const;
    QString host() const;

signals:

public slots:

private:
    Ui::LoginDialog * ui;
};

